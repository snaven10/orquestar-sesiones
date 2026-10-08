#!/usr/bin/env python3
"""orq — orquestador de sesiones Claude especializadas.

El orquestador es la sesión que hace spawn. Este script es su herramienta.
Nada se levanta sin un token emitido por `need` y aprobado por el usuario.
"""
import argparse, json, os, re, secrets, shlex, subprocess, sys, time, uuid
from pathlib import Path

HERE   = Path(__file__).resolve().parent
STATE  = Path.home() / ".orq"
CFG    = HERE / "roles.py"
TOKEN_TTL = 600  # 10 min


# ───────────────────────────── config ─────────────────────────────

# Host de ejecución: local (local, default) o remota (SSH). `--host` o ORQ_HOST.
HOST = os.environ.get("ORQ_HOST", "local")


def maq(cfg):
    """Config de la máquina activa."""
    return cfg["maquinas"][HOST]


def es_local(cfg):
    return not maq(cfg)["ssh"]


def bin_claude(cfg, host=None):
    """Binario de claude de la máquina. `ORQ_CLAUDE` lo reemplaza: es el gancho para probar
    spawn/scout con un claude FALSO sin tocar roles.py y sin arriesgar una sesión real."""
    return os.environ.get("ORQ_CLAUDE") or cfg["maquinas"][host or HOST]["claude"]


def flags_tools(a, quote=True):
    """`--allowedTools`/`--disallowedTools` de un arquetipo. Una sola construcción para spawn
    y scout. `quote=True` cuando el comando viaja por un script de shell (los tools llevan
    paréntesis y espacios: 'Bash(git *)'); `quote=False` cuando va como lista a subprocess."""
    q = shlex.quote if quote else (lambda s: s)
    fl = []
    for tool in a["tools"]:
        fl += ["--allowedTools", q(tool)]
    for tool in a.get("disallowed", []):
        fl += ["--disallowedTools", q(tool)]
    return fl


# Workspace activo. Lo fija main() con resolver_ws(); los comandos lo leen con ws_actual().
WS_NOMBRE = None


def resolver_ws(nombre_flag, cfg):
    """Qué workspace usa esta corrida: `--ws` -> el que contiene el cwd -> default.

    Con varios que contienen el cwd gana el de `path` más largo (el más específico).
    """
    wss = cfg["workspaces"]
    nombre = nombre_flag or os.environ.get("ORQ_WS")
    if nombre:
        if nombre not in wss:
            sys.exit(f"workspace `{nombre}` no existe. Declarados: {', '.join(wss)}")
        return nombre
    cwd = Path.cwd().resolve()
    cands = []
    for n, w in wss.items():
        raiz = Path(expand(w["path"])).resolve()
        if cwd == raiz or raiz in cwd.parents:
            cands.append((len(str(raiz)), n))
    return max(cands)[1] if cands else cfg["workspace_default"]


def ws_actual(cfg):
    """Config normalizada del workspace activo, con las rutas ya derivadas del `path`."""
    nombre = WS_NOMBRE or cfg["workspace_default"]
    w = dict(cfg["workspaces"][nombre])
    w["nombre"] = nombre
    w.setdefault("add_dir", None)           # solo MI-EMPRESA lo necesita (monorepo sin .git)
    w.setdefault("agents", f"{w['path']}/.claude/agents")
    w.setdefault("plans", f"{w['path']}/plans")
    w.setdefault("worktrees_en", f"~/.orq/trees/{nombre}")
    w["ruido"] = {r.lower() for r in w.get("ruido", [])}
    return w


def ws_ruta_target(cfg, target):
    """Ruta (en la máquina activa) de un target. En `repo` el target ES el workspace."""
    w = ws_actual(cfg)
    base = rpath(cfg, w["path"])
    return base if w["tipo"] == "repo" else f"{base}/{target}"


def clave_ws(cfg, clave):
    """Clave de estado de una sesión. Prefijada por ws salvo en MI-EMPRESA: `worker@X` de
    sessions.json existe desde antes de los workspaces y migrarla rompería los resume."""
    w = ws_actual(cfg)
    return clave if w.get("claves_sin_prefijo") else f"{w['nombre']}:{clave}"


def sesion_claude_ancestro():
    """sessionId del proceso claude que invoca a orq. CLAUDE_SESSION_ID no existe en el
    shell de la Bash tool; ~/.claude/sessions/<pid>.json sí, y el pid es un ancestro."""
    pid = os.getppid()
    for _ in range(12):
        f = Path.home() / ".claude" / "sessions" / f"{pid}.json"
        if f.exists():
            try:
                return json.loads(f.read_text()).get("sessionId")
            except Exception:
                return None
        try:
            pid = int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1])
        except Exception:
            return None
        if pid <= 1:
            return None
    return None


def load_cfg():
    """Config como módulo Python: cero dependencias (este python no tiene pip ni yaml)."""
    sys.path.insert(0, str(HERE))
    import roles
    return roles.CFG


def expand(p):
    return str(Path(os.path.expanduser(str(p))))


_RHOME = {}

def rpath(cfg, p):
    """Expande `~` contra el HOME REMOTO.

    shlex.quote('~/x') produce '~/x' literal y bash NO expande el tilde dentro de
    comillas: `[ -e '~/mi-empresa/...'/.git ]` siempre falla. Hay que resolver a ruta
    absoluta ANTES de citar.
    """
    p = str(p)
    if not p.startswith("~"):
        return p
    if "home" not in _RHOME:
        _, out, _ = remote(cfg, "echo $HOME")
        _RHOME["home"] = out.strip() or "/root"
    return _RHOME["home"] + p[1:]


# ───────────────────────────── shell ─────────────────────────────

def sh(cmd, cwd=None, stdin=None, timeout=120):
    """Corre local. Devuelve (rc, stdout, stderr)."""
    r = subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True,
                       text=True, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def remote(cfg, script, stdin=None, timeout=300):
    """Corre un script bash en la máquina activa: por SSH en remota, `bash -s` local en local."""
    ssh = maq(cfg)["ssh"]
    payload = script if stdin is None else script
    r = subprocess.run(ssh + ["bash", "-s"], input=payload,
                       capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


# ──────────────────────── descubrimiento ────────────────────────

def git(repo, *args, host=None, cfg=None):
    """git en un repo. Local o remoto según host."""
    if host:
        rc, out, _ = remote(cfg, f"git -C {shlex.quote(repo)} {' '.join(args)} 2>/dev/null")
        return out if rc == 0 else ""
    rc, out, _ = sh(["git", "-C", repo, *args])
    return out if rc == 0 else ""


def preflight(repo_path, cfg, host=None):
    """Estado REAL de un repo. Nunca confiar en el nombre de la carpeta."""
    q = shlex.quote(rpath(cfg, repo_path))
    script = f"""
    [ -e {q}/.git ] || {{ echo "NOREPO"; exit 0; }}
    echo "BRANCH=$(git -C {q} rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo "HEAD=$(git -C {q} rev-parse --short HEAD 2>/dev/null)"
    echo "DIRTY=$(git -C {q} status --porcelain 2>/dev/null | wc -l)"
    echo "RECENT=$(git -C {q} reflog --date=unix -1 2>/dev/null | grep -oE '\\{{[0-9]+\\}}' | tr -d '{{}}')"
    echo "PROCS=$(pgrep -fa claude 2>/dev/null | grep -c {shlex.quote(os.path.basename(repo_path))} || true)"
    """
    rc, out, _ = remote(cfg, script)
    if "NOREPO" in out:
        return None
    d = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
    dirty = int(d.get("DIRTY") or 0)
    # actividad reciente: reflog nuevo o proceso claude vivo sobre ese repo
    mins = None
    try:
        mins = (time.time() - int(d["RECENT"])) / 60
    except (KeyError, ValueError):
        pass
    umbral = cfg["preflight"]["actividad_reciente_min"]
    activo = (mins is not None and mins < umbral) or int(d.get("PROCS") or 0) > 0
    return {
        "branch": d.get("BRANCH", "?"), "head": d.get("HEAD", "?"),
        "dirty": dirty, "mins_desde_reflog": round(mins) if mins is not None else None,
        "activo": activo,
    }


def descubrir_targets(cfg, host=None):
    """Repos git bajo el workspace. Se DESCUBREN, no se declaran."""
    w = ws_actual(cfg)
    if w["tipo"] == "repo":
        return [os.path.basename(w["path"].rstrip("/"))]   # el repo es su propio target
    ws = rpath(cfg, w["path"])
    # El `for` devuelve el estado del ULTIMO comando: si el ultimo directorio del
    # workspace no es repo, `[ -e ] &&` da falso y el loop sale 1 — y se descartaban
    # los 34 targets buenos. Con `if/fi` el rc solo refleja fallas REALES (ssh caido).
    rc, out, _ = remote(cfg, f"for d in {shlex.quote(ws)}/*/; do "
                             f"if [ -e \"$d/.git\" ]; then basename \"$d\"; fi; done")
    return [l for l in out.splitlines() if l] if rc == 0 else []


def detectar_recursos(intent, cfg):
    """Recursos exclusivos que el trabajo va a tocar, por palabras clave."""
    hits, low = [], intent.lower()
    for nombre, r in (cfg.get("recursos_exclusivos") or {}).items():
        for pat in r.get("detectar", []):
            if pat.lower().strip("*").strip(".") in low:
                hits.append((nombre, r["motivo"]))
                break
    return hits


ic = lambda s: s.lower()


def menciona(target, intent, ruido=frozenset()):
    """¿El intent nombra este repo? Por token, no por substring.

    `api-plantillas` no es substring de "backfill de plantillas", pero el token
    `plantillas` sí está. Match exacto del nombre completo, o de un token propio.
    """
    low = ic(intent)
    if ic(target) in low:
        return True
    toks = [t for t in re.split(r"[_\-]+", ic(target)) if len(t) >= 4 and t not in ruido]
    # El cierre \b es obligatorio: sin él el token es un PREFIJO y matchea de más.
    # Caso real: el token `config` de `auth-service-config` disparaba con un
    # intent que decía `configuracionDependencia`, y proponía worker+reviewer en un
    # repo que no tenía nada que ver.
    return any(re.search(rf"\b{re.escape(t)}\b", low) for t in toks)


def corta(s, n):
    """Trunca para que la tabla no se desborde: si se desborda, no se lee."""
    s = str(s)
    return s if len(s) <= n else s[:n - 1] + "…"


# ──────────────── specialists: overlay, catálogo y match (PLAN-001 DD-2/DD-3) ────────────────
# Resolución en escalones: 1) CONFIRMADO (overlay del usuario, luego roles.py) · 2) MATCH
# (candidatos del disco, solo se PROPONEN) · 3) SCOUT (investigar; es de otra task).

def cargar_overlay():
    """Mapeos que el usuario confirmó: {"<ws>": {"arq@target": "agente"}}. Vive en ~/.orq y no
    en roles.py para que confirmar un match no obligue a editar la política a mano."""
    return _load("specialists.json", {})


def guardar_overlay(data):
    _save("specialists.json", data)


def parse_frontmatter(texto):
    """Frontmatter de un agente SIN yaml (este python no tiene pip). Soporta lo que usan los
    agentes reales: `clave: valor`, valores entre comillas, bloques `>`/`|` (multilínea),
    escalares partidos en varias líneas indentadas y listas `- item`. Devuelve {} si no hay."""
    lineas = texto.replace("\r\n", "\n").split("\n")
    if not lineas or lineas[0].strip() != "---":
        return {}
    try:
        fin = next(i for i in range(1, len(lineas)) if lineas[i].strip() == "---")
    except StopIteration:
        return {}                      # sin cierre: no se adivina dónde termina
    fm, clave, partes, bloque = {}, None, [], None

    def cerrar():
        if clave is not None:
            sep = "\n" if bloque == "|" else " "
            v = sep.join(x for x in partes if x != "").strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            fm[clave] = v

    for ln in lineas[1:fin]:
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", ln)
        if m and not ln[:1].isspace():
            cerrar()
            clave, v = m.group(1), m.group(2).strip()
            bloque = v[0] if v[:1] in (">", "|") else None
            partes = [] if bloque else [v]
        elif clave is not None:
            t = ln.strip()
            if t.startswith("- "):     # item de lista: se une con comas
                t = t[2:].strip()
                prev = [i for i, x in enumerate(partes) if x]
                if prev:
                    partes[prev[-1]] += ","
            partes.append(t)
    cerrar()
    return fm


def dirs_agentes(cfg, target=None):
    """Dirs de agentes alcanzables con los flags de spawn, en orden de precedencia, como
    [(Path, scope)]: p = del repo (se resuelve por cwd) · m = del workspace (exige --add-dir)
    · g = global. Un dir repetido (en `repo`, p y ws.agents son el mismo) se cuenta una vez."""
    w = ws_actual(cfg)
    base = Path(expand(w["path"]))
    out = []
    if w["tipo"] == "repo":
        out.append((base / ".claude" / "agents", "p"))
    else:
        if target:
            out.append((base / target / ".claude" / "agents", "p"))
        out.append((Path(expand(w["agents"])), "m"))
    out.append((Path(expand("~/.claude/agents")), "g"))
    vistos, res = set(), []
    for d, sc in out:
        k = str(d.resolve()) if d.exists() else str(d)
        if k not in vistos:
            vistos.add(k); res.append((d, sc))
    return res


def catalogo_agentes(cfg, target=None):
    """Agentes en disco -> [{name, description, model, path, scope}]. Si un nombre aparece en
    varios dirs gana el de scope más cercano al repo (el mismo orden que usa claude)."""
    vistos, cat = set(), []
    for d, sc in dirs_agentes(cfg, target):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):      # `*.md.bak2` no matchea: los backups no cuentan
            fm = parse_frontmatter(f.read_text(errors="ignore"))
            nombre = fm.get("name") or f.stem
            if nombre in vistos:
                continue
            vistos.add(nombre)
            cat.append({"name": nombre, "description": fm.get("description", ""),
                        "model": fm.get("model", ""), "path": str(f), "scope": sc})
    return cat


def señales_target(cfg, target):
    """Tags de stack del repo según roles.py["señales"]. Se lee el disco LOCAL (igual que el
    catálogo de agentes); un target inexistente da [] y el match simplemente no propone nada."""
    w = ws_actual(cfg)
    base = Path(expand(w["path"]))
    repo = base if w["tipo"] == "repo" else base / target
    tags = []
    for regla in cfg.get("señales", []):
        for nombre in regla["archivos"]:
            f = repo / nombre
            if not f.is_file():
                continue
            tags += regla.get("tags", [])
            if regla.get("contiene"):
                txt = f.read_text(errors="ignore").lower()
                for needle, extra in regla["contiene"].items():
                    if needle.lower() in txt:
                        tags += extra
            break                         # un marcador por regla alcanza (pom O gradle)
    return list(dict.fromkeys(tags))      # sin duplicados, conserva el orden


def puntuar(agente, tags, arquetipo, cfg, usados=frozenset()):
    """Afinidad 0..1 = tags (del target + el rol del arquetipo) hallados en name+description
    del agente / total de tags. Bonus +0.1 si ese agente ya está mapeado en el ws.
    Devuelve (score, [tags que matchearon])."""
    texto = f"{agente['name']} {agente['description']}".lower()
    alias = cfg.get("tags_alias", {})
    total, hit = [], []
    for t in tags:
        total.append(t)
        pats = alias.get(t, [t])
        if any(re.search(rf"(?<![\w]){re.escape(a)}(?![\w])", texto) for a in pats):
            hit.append(t)
    rol = (cfg.get("arquetipo_señales") or {}).get(arquetipo)
    if rol:
        total.append(arquetipo)
        if any(re.search(rf"(?<![\w]){re.escape(r)}", texto) for r in rol):
            hit.append(arquetipo)
    if not total:
        return 0.0, []
    score = len(hit) / len(total)
    if hit and agente["name"] in usados:   # el bonus solo desempata, nunca crea un match de la nada
        score = min(1.0, score + 0.1)
    return round(score, 2), hit


def resolver_specialist(arquetipo, target, cfg):
    """-> {nombre|None, origen: overlay|roles|-, candidatos: [(nombre, score, tags)], aviso}.

    `nombre` solo viene si el agente EXISTE como .md alcanzable: un mapeo a un agente que no
    está en disco antes caía a sesión genérica en silencio; ahora es un faltante con aviso.
    Los candidatos se calculan solo cuando no hay nombre, y nunca se autoasignan."""
    ws = ws_actual(cfg)["nombre"]
    ov = cargar_overlay().get(ws, {})
    sp = cfg.get("specialists") or {}
    k, kw = f"{arquetipo}@{target}", f"{arquetipo}@*"
    mapeado, origen = None, "-"
    for fuente, tabla in (("overlay", ov), ("roles", sp)):
        n = tabla.get(k) or tabla.get(kw)
        if n:
            mapeado, origen = n, fuente
            break
    cat = catalogo_agentes(cfg, target)
    res = {"nombre": None, "origen": "-", "candidatos": [], "aviso": None}
    if mapeado and any(a["name"] == mapeado for a in cat):
        res.update(nombre=mapeado, origen=origen)
        return res
    if mapeado:
        res["aviso"] = (f"mapeado a `{mapeado}` ({origen}) pero no existe como .md alcanzable: "
                        f"{' · '.join(str(d) for d, _ in dirs_agentes(cfg, target))}")
    usados = (set(ov.values()) | set(sp.values())) - ({mapeado} if mapeado else set())
    tags = señales_target(cfg, target)
    umbral = cfg.get("match_umbral", 0.5)
    pun = []
    for a in cat:
        sc, hit = puntuar(a, tags, arquetipo, cfg, usados)
        if sc >= umbral and hit:
            pun.append((a["name"], sc, hit))
    pun.sort(key=lambda x: (-x[1], x[0]))   # empate: orden alfabético, determinístico
    res["candidatos"] = pun[:3]
    return res


def texto_scopes(cfg):
    """Scopes donde se puede guardar un agente nuevo, según el tipo de workspace (DD-5):
    en `repo` no hay monorepo, así que solo [p] y [g]."""
    w = ws_actual(cfg)
    if w["tipo"] == "repo":
        l = [f"    [p] proyecto  {w['path']}/.claude/agents/   solo este repo"]
    else:
        l = ["    [p] proyecto  <repo>/.claude/agents/      solo ese repo",
             f"    [m] monorepo  {w['agents']}/     exige --add-dir {w['add_dir']}"]
    l.append("    [g] global    ~/.claude/agents/           contamina otros proyectos")
    return l


def lineas_candidatos(clave, r, sangria="      "):
    """Qué mostrar bajo un faltante: aviso, top 3 con sus tags, o la salida a `scout`."""
    out = []
    if r.get("aviso"):
        out.append(f"{sangria}⚠ {r['aviso']}")
    if r["candidatos"]:
        out.append(f"{sangria}candidatos del disco (propuestos, NO asignados):")
        for n, sc, tg in r["candidatos"]:
            out.append(f"{sangria}  {n:<34}{sc:<6.2f}[{', '.join(tg)}]")
        out.append(f"{sangria}confirmar: orq agent use {r['candidatos'][0][0]} {clave}")
    else:
        out.append(f"{sangria}sin candidatos → candidato a scout (ver SCOUTS PROPUESTOS)")
    return out


def scouts_de(faltantes, cfg):
    """Escalón 3: un scout por faltante SIN candidatos del disco. Si hay un candidato, el
    camino barato es `agent use`; investigar solo se ofrece cuando no queda otra."""
    sc = cfg["arquetipos"]["scout"]
    vistos, out = set(), []
    for clave, rs in faltantes:
        if rs["candidatos"] or clave in vistos:
            continue
        vistos.add(clave)
        arq, tgt = clave.split("@", 1)
        out.append({"arquetipo": arq, "target": tgt, "clave": clave, "costo": sc["costo"]})
    return out


def imprimir_scouts(scouts, tok):
    if not scouts:
        return
    print("\n  🔎 SCOUTS PROPUESTOS (investigan el repo y dejan un BORRADOR; no guardan nada):")
    for i, s_ in enumerate(scouts, 1):
        c = s_["costo"]
        print(f"    S{i} {s_['clave']:<40} ~${c[0]:.2f}–{c[1]:.2f}  local · sonnet · solo lectura")
    print(f"    cuesta plata: necesita aval →  orq scout --token {tok} --only N")


# ──────────────────── política de árbol ────────────────────

AUDITORES = {"reviewer", "validator", "qa"}


def clasificar(arquetipo, intent, pf, n_workers_mismo_repo=1):
    """¿Qué clase de trabajo es? De acá sale la decisión de árbol."""
    if arquetipo in AUDITORES:
        # La pregunta que decide: ¿lo que se audita está commiteado?
        # Si el árbol tiene cambios sucios, lo que interesa revisar está AHÍ,
        # y un worktree nuevo no los vería nunca.
        sin_commitear = pf.get("dirty", 0) > 0 or re.search(
            r"\b(sin commitear|no commiteado|antes de commitear|working tree|"
            r"lo que llevo|lo que va|wip)\b", intent, re.I)
        return "auditar_sin_commitear" if sin_commitear else "auditar_commiteado"
    return "implementar_paralelo" if n_workers_mismo_repo > 1 else "implementar_simple"


def decidir_arbol(modo, cfg, pf):
    """Devuelve (etiqueta, necesita_worktree, pregunta_al_usuario)."""
    pol = cfg["politica_arbol"][modo]

    if modo == "auditar_sin_commitear":
        return ("árbol principal — OBLIGATORIO", False, None)

    if modo == "auditar_commiteado":
        return (f"worktree detached @ {pf.get('head','?')}", True, None)

    if modo == "implementar_simple":
        rama = pf.get("branch", "?")
        return ("A DEFINIR", False,
                f"¿sobre la rama actual `{rama}`, sobre otra rama, o en un worktree nuevo?")

    # implementar_paralelo
    return (f"worktree + rama nueva (base: {pf.get('branch','?')})", True,
            "si estas tareas NO tocan los mismos archivos, ¿igual querés el worktree?")


# ───────────────────────────── estado ─────────────────────────────

def _load(name, default):
    p = STATE / name
    return json.loads(p.read_text()) if p.exists() else default


def _save(name, data):
    p = STATE / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))


# ───────────────────────────── need ─────────────────────────────

def cmd_need(args):
    cfg = load_cfg()
    if args.plan:
        return need_de_plan(args, cfg)
    intent = args.intent
    sesiones = _load("sessions.json", {})
    wsd = ws_actual(cfg)
    targets = descubrir_targets(cfg)

    # qué targets toca este trabajo: mención explícita, o los que tengan cambios
    tocados = [t for t in targets if menciona(t, intent, wsd["ruido"])]
    estados = {}
    for t in targets:
        pf = preflight(ws_ruta_target(cfg, t), cfg)
        if pf:
            estados[t] = pf
    if not tocados:
        tocados = [t for t, s in estados.items() if s["dirty"] > 0 or s["activo"]]
    if not tocados:
        print("No pude inferir el target. Nombrá el repo en el intent.")
        print("Repos disponibles:", ", ".join(targets))
        return 1

    propuesta, faltantes = [], []
    for t in tocados:
        for arq in ("worker", "reviewer"):
            rs = resolver_specialist(arq, t, cfg)
            sp = rs["nombre"]
            key = f"{arq}@{t}"
            pf = estados.get(t, {})
            persist = cfg["arquetipos"][arq]["persist"]
            ks = clave_ws(cfg, key)
            estado = ("resume " + sesiones[ks][:8]) if (persist and ks in sesiones) else "crear"
            modo = clasificar(arq, intent, pf, n_workers_mismo_repo=args.paralelo)
            arbol, necesita_wt, pregunta = decidir_arbol(modo, cfg, pf)
            propuesta.append({"arquetipo": arq, "target": t, "specialist": sp,
                              "origen": rs["origen"], "candidatos": rs["candidatos"],
                              "estado": estado, "arbol": arbol, "modo": modo,
                              "worktree": necesita_wt, "pregunta": pregunta,
                              "branch": pf.get("branch"), "head": pf.get("head")})
            if not sp:
                faltantes.append((key, rs))

    recursos = detectar_recursos(intent, cfg)
    costo = 0.12 * len(propuesta)
    tok = "T-" + secrets.token_hex(3)       # antes de imprimir: la sección de scouts lo cita
    scouts = scouts_de(faltantes, cfg)

    # ── tabla ──
    print(f"\n  Intent: {intent}\n")
    print(f"  Detectado en {HOST}:")
    for t in tocados:
        s = estados.get(t, {})
        marca = " ⚠ ACTIVO" if s.get("activo") else ""
        print(f"    {t:<34} [{s.get('branch','?')}] {s.get('head','')} "
              f"dirty={s.get('dirty',0)}{marca}")
    print(f"\n  PROPUESTA — verificá antes de confirmar:\n")
    print(f"    {'#':<3}{'ARQUETIPO':<11}{'TARGET':<32}{'SPECIALIST':<30}{'ORIGEN':<9}{'ÁRBOL':<40}{'ESTADO'}")
    for i, p in enumerate(propuesta, 1):
        sp = p["specialist"] or "❌ SIN SPECIALIST"
        print(f"    {i:<3}{p['arquetipo']:<11}{corta(p['target'],30):<32}"
              f"{corta(sp,28):<30}{p['origen']:<9}{corta(p['arbol'],38):<40}{p['estado']}")

    preguntas = [(i, p) for i, p in enumerate(propuesta, 1) if p.get("pregunta")]
    if preguntas:
        print("\n  ❓ EL USUARIO DEBE DEFINIR (no lo decidas vos):")
        for i, p in preguntas:
            print(f"    #{i} {p['arquetipo']}@{p['target']}: {p['pregunta']}")

    oblig = [p for p in propuesta if p["modo"] == "auditar_sin_commitear"]
    if oblig:
        print("\n  ⚠ ÁRBOL PRINCIPAL OBLIGATORIO en %d sesión(es): hay cambios sin" % len(oblig))
        print("    commitear y un worktree nuevo NO los vería (checkout limpio del commit).")

    wt = [p for p in propuesta if p["worktree"]]
    if wt:
        print("\n  ➕ WORKTREES a crear: %d" % len(wt))
        print("    Al crearlos hay que PREGUNTAR su política de destrucción:")
        print("    [n] nunca automático   [l] al terminar si está limpio   [m] tras merge")

    if recursos:
        print("\n  🔒 RECURSOS EXCLUSIVOS detectados (se serializan, NO van en paralelo):")
        for n, m in recursos:
            print(f"    · {n}: {m}")

    if faltantes:
        print("\n  ❌ FALTAN SPECIALISTS:")
        for f, rs in faltantes:
            print(f"    · {f}")
            for l in lineas_candidatos(f, rs):
                print(l)
        print("\n  La skill debe PROPONER su estructura (devctx + memoria histórica +")
        print("  context7 + claude-automation-recommender) y PREGUNTAR el scope:")
        for l in texto_scopes(cfg):
            print(l)
    imprimir_scouts(scouts, tok)

    conc = maq(cfg)["concurrencia"]
    print(f"\n  Concurrencia máx {HOST}: {conc}"
          f"{'  ⚠ la propuesta la excede, se parte en olas' if len(propuesta) > conc else ''}")
    print(f"  Costo estimado de arranque: ~${costo:.2f}  ({len(propuesta)} sesiones × ~$0.12)")

    _save(f"tokens/{tok}.json", {"intent": intent, "propuesta": propuesta, "ws": wsd["nombre"],
                                 "recursos": [r[0] for r in recursos], "scouts": scouts,
                                 "emitido": time.time()})
    print(f"\n  token: {tok}   (vence en {TOKEN_TTL//60} min)")
    print("  [a] aprobar → orq spawn --token %s   [q]uitar N   [m]odificar N   [c]ancelar\n" % tok)
    return 0


def need_de_plan(args, cfg):
    """Propuesta a partir de un LOTE declarado en el master de un PLAN.

    El PLAN ya dice qué specialist y qué modelo lleva cada task: no se adivina.
    """
    data, err = propuesta_de_lote(args.plan, args.lote, cfg)
    if err:
        print(f"  {err}"); return 1
    prop, por_repo = data["prop"], data["por_repo"]
    pdir_nombre = data["pdir_nombre"]
    if not prop:
        print(f"  el lote {data['lote']} no tiene tasks pendientes"); return 1

    wsd = ws_actual(cfg)
    # catálogo por target: el agente de proyecto de un repo no se ve desde otro
    cats = {r: {a["name"]: a for a in catalogo_agentes(cfg, r)} for r in por_repo}
    pfs = {r: (preflight(ws_ruta_target(cfg, r), cfg) or {}) for r in por_repo}

    print(f"\n  PLAN-{args.plan} · lote {data['lote']}  —  {len(prop)} sesiones\n")
    print(f"  Estado real en {HOST}:")
    for r, pf in pfs.items():
        print(f"    {r:<26} [{pf.get('branch','?')}] {pf.get('head','')} "
              f"dirty={pf.get('dirty',0)}{'  ⚠ ACTIVO' if pf.get('activo') else ''}")

    print(f"\n  PROPUESTA — verificá antes de confirmar:\n")
    print(f"    {'#':<3}{'TASK':<9}{'SPECIALIST':<38}{'ORIGEN':<9}{'MOD':<8}{'REPO':<18}{'QUÉ'}")
    faltan, faltan_t = [], {}
    tok = "T-" + secrets.token_hex(3)
    scouts = []
    for i, p_ in enumerate(prop, 1):
        sp = p_["specialist"]
        ok = sp in cats.get(p_["target"], {})
        # el specialist lo declara el PLAN: su origen es el plan, no el overlay ni roles.py
        p_["origen"] = "plan" if ok else "-"
        if not ok:
            faltan.append(sp)
            faltan_t.setdefault(sp, p_["target"])
        n = len([x for x in prop if x["target"] == p_["target"]])
        p_["modo"] = "implementar_paralelo" if n > 1 else "implementar_simple"
        pf = pfs.get(p_["target"], {})
        p_["branch"], p_["head"] = pf.get("branch"), pf.get("head")
        p_["worktree"], p_["pregunta"] = False, None
        p_["arbol"] = "A DEFINIR (--rama / --arbol)"
        print(f"    {i:<3}{p_['task']:<9}{('✅ ' if ok else '❌ ')+corta(sp,34):<38}{p_['origen']:<9}"
              f"{corta(p_['modelo'],6):<8}{corta(p_['target'],16):<18}{corta(p_['titulo'],42)}")

    if data.get("ramas") or data.get("bases"):
        print(f"\n  El PLAN declara:  rama `{', '.join(data['ramas']) or '—'}`"
              f"   ·   base `{', '.join(data['bases']) or '—'}`")
        print(f"    → pasalo tal cual:  --rama {(data['ramas'] or ['?'])[0]} "
              f"--base {(data['bases'] or ['?'])[0]}")

    cubiertas = [p_ for p_ in prop if re.search(r"worktree", p_["titulo"], re.I)]
    if cubiertas:
        print(f"\n  ⚠ {', '.join('TASK-'+c['task'] for c in cubiertas)} es la creación de worktrees,")
        print(f"    que `orq` ya hace al lanzar. Si la lanzás igual, se duplica: usá --only para excluirla.")

    if data["saltadas"]:
        print(f"\n  Fuera (ya cerradas): {', '.join(data['saltadas'])}")
    if faltan:
        print(f"\n  ❌ El plan pide specialists que NO existen: {', '.join(sorted(set(faltan)))}")
        print("     Proponé su estructura y PREGUNTÁ el scope antes de lanzar:")
        for l in texto_scopes(cfg):
            print(l)
        for n in sorted(set(faltan)):
            # el PLAN pide un nombre concreto: se busca algo parecido para ESE repo
            print(f"    · {n}")
            rs = resolver_specialist("worker", faltan_t[n], cfg)
            rs["aviso"] = None
            for l in lineas_candidatos(f"worker@{faltan_t[n]}", rs):
                print(l)
            scouts += scouts_de([(f"worker@{faltan_t[n]}", rs)], cfg)
        scouts = [x for k, x in enumerate(scouts) if x["clave"] not in {y["clave"] for y in scouts[:k]}]
        imprimir_scouts(scouts, tok)
    for r, n in por_repo.items():
        if n > 1:
            print(f"\n  ⚠ {n} sesiones sobre {r}. Si comparten árbol pueden tragarse")
            print(f"    ediciones entre ellas al commitear. Definí --rama/--base o --arbol.")

    print(f"\n  Condición de desbloqueo del lote (PROSA del master, leela):")
    print(f"    {re.sub(chr(10), ' ', data['condicion'])[:300]}")
    conc = maq(cfg)["concurrencia"]
    print(f"\n  Concurrencia máx {HOST}: {conc}"
          f"{'   ⚠ la excede' if len(prop) > conc else ''}")
    print(f"  Costo estimado de arranque: ~${0.12*len(prop):.2f}")

    _save(f"tokens/{tok}.json", {"intent": f"PLAN-{args.plan} lote {data['lote']}",
                                 "propuesta": prop, "recursos": [], "plan": str(args.plan), "ws": wsd["nombre"],
                                 "scouts": scouts,
                                 "plan_dir": pdir_nombre, "emitido": time.time()})
    print(f"\n  token: {tok}   (vence en {TOKEN_TTL//60} min)")
    print(f"  [a] aprobar → orq spawn --token {tok} ...   [c]ancelar\n")
    return 0


# ───────────────────────────── spawn ─────────────────────────────

def enlazar_agentes(cfg, wdir):
    """Un worktree nace SIN `.claude/`, y en modo --bg la resolución del agente NO
    ve el `--add-dir`: la sesión arranca con "no agent named ... — spawning with
    default template", o sea genérica. En `-p` sí resuelve; el problema es sólo de
    --bg. Se le cuelga al worktree su propio `.claude/agents` apuntando al del
    workspace. Verificado: sin el symlink falla, con él arranca especializada."""
    w = ws_actual(cfg)
    if w["tipo"] == "repo":
        return      # el `.claude/agents` del repo ya viaja en el checkout del worktree
    agents = rpath(cfg, w["agents"])
    W = shlex.quote(wdir)
    remote(cfg, f"""
mkdir -p {W}/.claude
ln -sfn {shlex.quote(agents)} {W}/.claude/agents
gd=$(git -C {W} rev-parse --git-dir 2>/dev/null) && mkdir -p "$gd/info" && \
  grep -qx '.claude/' "$gd/info/exclude" 2>/dev/null || echo '.claude/' >> "$gd/info/exclude"
""")


def cmd_spawn(args):
    cfg = load_cfg()
    tp = STATE / "tokens" / f"{args.token}.json"
    if not tp.exists():
        print(f"token {args.token} inválido o ya usado. Corré `orq need` primero.", file=sys.stderr)
        return 2
    t = json.loads(tp.read_text())
    if time.time() - t["emitido"] > TOKEN_TTL:
        tp.unlink()
        print("token vencido. Corré `orq need` de nuevo.", file=sys.stderr)
        return 2

    # El token manda: se aprobó para UN workspace y spawn no puede caer en otro por el cwd.
    global WS_NOMBRE
    if t.get("ws"):
        WS_NOMBRE = t["ws"]
    wsd = ws_actual(cfg)
    planes = rpath(cfg, wsd["plans"])
    add_dir = rpath(cfg, wsd["add_dir"]) if wsd["add_dir"] else None
    flags_add_dir = ["--add-dir", add_dir] if add_dir else []
    claude = bin_claude(cfg)
    sesiones = _load("sessions.json", {})
    jobs = _load("jobs.json", {})
    padre = os.environ.get("CLAUDE_SESSION_ID") or sesion_claude_ancestro() or "orq-local"
    lanzados = []

    propuesta = t["propuesta"]
    if args.only:
        idx = {int(i) for i in args.only.split(",")}
        propuesta = [p for i, p in enumerate(propuesta, 1) if i in idx]
        if not propuesta:
            print(f"--only {args.only} no selecciona nada de la propuesta", file=sys.stderr)
            return 2
        print(f"  (--only {args.only}: {len(propuesta)} de {len(t['propuesta'])} sesiones)\n")

    # Preguntas sin responder => no se levanta nada. El usuario define, no el script.
    pend = [p for p in propuesta if p.get("pregunta") and not (args.arbol or args.rama)]
    if pend:
        print("  Falta definir el árbol de %d sesión(es). Pasá --arbol:" % len(pend), file=sys.stderr)
        for p in pend:
            print(f"    {p['arquetipo']}@{p['target']}: {p['pregunta']}", file=sys.stderr)
        print("    --arbol rama_actual | otra:<nombre> | worktree", file=sys.stderr)
        return 2

    # Si se van a crear worktrees, su política de destrucción se define ANTES.
    van_wt = [p for p in propuesta if p.get("worktree")] or \
             (list(propuesta) if args.arbol == "worktree" else [])
    if args.rama:
        van_wt = [p for p in propuesta if p["modo"] != "auditar_sin_commitear"]
    if van_wt and not args.destruccion:
        print(f"  Se crearían {len(van_wt)} worktree(s) y falta su política de destrucción.",
              file=sys.stderr)
        print("    --destruccion nunca | si_limpio | tras_merge", file=sys.stderr)
        return 2

    if t.get("plan_dir"):
        pd = f"{planes}/{t['plan_dir']}"
        rc_p, out_p, _ = remote(cfg, f"[ -d {shlex.quote(pd)} ] && "
                                     f"ls {shlex.quote(pd)}/tasks/*.md 2>/dev/null | wc -l || echo NOEXISTE")
        if "NOEXISTE" in out_p or out_p.strip() in ("", "0"):
            print(f"  ❌ El PLAN no existe en {HOST}: {pd}", file=sys.stderr)
            print(f"     Las sesiones corren ALLÁ y no lo encontrarían. Sincronizalo:", file=sys.stderr)
            print(f"     scp -r -o ClearAllForwardings=yes "
                  f"{wsd['plans']}/{t['plan_dir']} remota:{wsd['plans'].removeprefix('~/')}/", file=sys.stderr)
            return 2
        print(f"  ✓ PLAN presente en {HOST} ({out_p.strip()} tasks)")

    wts = _load("worktrees.json", {})

    for p in propuesta:
        arq, tgt = p["arquetipo"], p["target"]
        key = clave_ws(cfg, f"p{p['plan']}-task{p['task']}@{tgt}" if p.get("plan") else
                       f"task{p['task']}@{tgt}" if p.get("task") else f"{arq}@{tgt}")
        a = cfg["arquetipos"][arq]
        jid = secrets.token_hex(4)
        bgname = None
        principal = ws_ruta_target(cfg, tgt)
        cwd = principal

        # --arbol otra:<rama> => checkout EN EL ÁRBOL PRINCIPAL. Eso muta un árbol
        # compartido: solo se permite si está limpio y sin actividad reciente.
        if p.get("pregunta") and (args.arbol or "").startswith("otra:"):
            destino = args.arbol.split(":", 1)[1].strip()
            if not destino:
                print("  ❌ --arbol otra:<nombre> sin nombre de rama"); continue
            pf_now = preflight(principal, cfg) or {}
            if pf_now.get("dirty", 0) > 0 or pf_now.get("activo"):
                print(f"  ❌ {key}: no puedo cambiar a `{destino}` en el árbol principal "
                      f"(dirty={pf_now.get('dirty',0)}, activo={pf_now.get('activo')}). "
                      f"Usá --arbol worktree.")
                continue
            rc_c, out_c, err_c = remote(cfg,
                f"git -C {shlex.quote(principal)} checkout {shlex.quote(destino)} 2>&1 || "
                f"git -C {shlex.quote(principal)} checkout -b {shlex.quote(destino)} 2>&1")
            if rc_c != 0 or "error" in (out_c + err_c).lower():
                print(f"  ❌ {key}: falló el checkout de `{destino}`: {(out_c or err_c)[:160]}")
                continue
            print(f"  ↪ árbol principal movido a `{destino}`")

        # --rama: UN worktree por repo, compartido por todas las sesiones de ese repo,
        # con rama fija y base explícita. Es el modelo de los PLAN que declaran sus propias
        # ramas (p.ej. PLAN-040 TASK-008: "uno por repo, desde gitlab/staging").
        if args.rama and p["modo"] != "auditar_sin_commitear":
            base = args.base or p.get("branch") or "HEAD"
            wdir = (f"{rpath(cfg, wsd['worktrees_en'])}/{tgt}/"
                    f"{re.sub(r'[^A-Za-z0-9._-]+', '-', args.rama)}")
            W, P, R, B = map(shlex.quote, (wdir, principal, args.rama, base))
            # la ref remota local puede estar VIEJA (remota tenía gitlab/staging=f5b7ba8f
            # con el remoto real en 08e95e9d): fetch SIEMPRE antes de ramificar.
            fetch = ""
            if "/" in base and not re.fullmatch(r"[0-9a-f]{7,40}", base):
                rem, br = base.split("/", 1)
                fetch = f"git -C {P} fetch -q {shlex.quote(rem)} {shlex.quote(br)} 2>&1 | tail -2"
            rc_w, out_w, _ = remote(cfg, f"""
{fetch}
if [ -d {W} ]; then
  cur=$(git -C {W} rev-parse --abbrev-ref HEAD)
  if [ "$cur" = {R} ]; then echo "ESTADO=reusado"; else echo "ESTADO=otra_rama:$cur"; fi
else
  mkdir -p "$(dirname {W})"
  if git -C {P} show-ref --verify --quiet refs/heads/{args.rama}; then
    git -C {P} worktree add {W} {R} 2>&1 | tail -1
  else
    git -C {P} worktree add -b {R} {W} {B} 2>&1 | tail -1
  fi
  [ -d {W} ] && echo "ESTADO=creado" || echo "ESTADO=fallo"
fi
echo "SHA=$(git -C {W} rev-parse --short HEAD 2>/dev/null)"
echo "BASE=$(git -C {P} rev-parse --short {B} 2>/dev/null)"
git -C {W} merge-base --is-ancestor {B} HEAD 2>/dev/null && echo "ANCESTRO=ok" || echo "ANCESTRO=FALLA"
""")
            kv = dict(l.split("=", 1) for l in out_w.splitlines() if "=" in l and l.split("=")[0].isupper())
            est = kv.get("ESTADO", "fallo")
            if est.startswith("otra_rama") or est == "fallo" or kv.get("ANCESTRO") != "ok":
                print(f"  ❌ {key}: worktree {wdir} → {est}, ancestro de {base}: {kv.get('ANCESTRO')}")
                print(f"     {out_w[-300:]}")
                continue
            enlazar_agentes(cfg, wdir)
            cwd = wdir
            reg = wts.setdefault(wdir, {"target": tgt, "rama": args.rama, "desde": base, "ws": wsd["nombre"],
                                        "base_sha": kv.get("BASE"), "sesiones": [],
                                        "destruccion": args.destruccion, "creado": time.time()})
            if key not in reg.setdefault("sesiones", []):   # sin duplicar por relanzamiento
                reg["sesiones"].append(key)
            print(f"  {'➕' if est == 'creado' else '♻'} worktree {est}: {wdir}")
            print(f"     rama {args.rama} @ {kv.get('SHA')}  ·  base {base} = {kv.get('BASE')}  ·  ancestro ✓")

        # --arbol worktree explícito se honra venga de donde venga la propuesta: cmd_need
        # pisa `pregunta`/`worktree` en las propuestas por PLAN (el plan ya declara rama/base).
        usa_wt = not args.rama and (p.get("worktree") or args.arbol == "worktree")
        if usa_wt:
            slug = re.sub(r"[^a-z0-9]+", "-", f"{arq}-{int(time.time())%100000}".lower())
            wdir = f"{rpath(cfg, wsd['worktrees_en'])}/{tgt}/{slug}"
            if p["modo"] == "auditar_commiteado":
                # detached en el SHA: revisión determinista, no crea rama
                add = f"git -C {shlex.quote(principal)} worktree add --detach " \
                      f"{shlex.quote(wdir)} {shlex.quote(p.get('head') or 'HEAD')}"
                rama = f"detached@{p.get('head')}"
            else:
                # rama nueva. Base: --base si se pasó (con fetch: la ref local puede estar
                # vieja), si no la rama ACTUAL del árbol (no development).
                base = args.base or p.get("branch") or "HEAD"
                if p.get("plan"):
                    slug = f"plan-{p['plan']}-task-{p['task']}"
                    wdir = f"{rpath(cfg, wsd['worktrees_en'])}/{tgt}/{slug}"
                    rama = f"feature/{slug}"
                else:
                    rama = f"orq/{slug}"
                fetch = ""
                if "/" in base and not re.fullmatch(r"[0-9a-f]{7,40}", base):
                    rem, br = base.split("/", 1)
                    fetch = (f"git -C {shlex.quote(principal)} fetch -q {shlex.quote(rem)} "
                             f"{shlex.quote(br)} && ")
                add = fetch + f"git -C {shlex.quote(principal)} worktree add -b {shlex.quote(rama)} " \
                      f"{shlex.quote(wdir)} {shlex.quote(base)}"
            rc_w, out_w, err_w = remote(cfg, f"mkdir -p $(dirname {shlex.quote(wdir)}) && {add} 2>&1")
            if rc_w != 0 or "fatal" in (out_w + err_w).lower():
                print(f"  ❌ no pude crear el worktree de {key}: {(out_w or err_w)[:200]}")
                continue
            enlazar_agentes(cfg, wdir)
            cwd = wdir
            wts[wdir] = {"target": tgt, "rama": rama, "desde": args.base or p.get("branch"),
                         "sesion": key, "ws": wsd["nombre"], "destruccion": args.destruccion,
                         "creado": time.time()}
            print(f"  ➕ worktree {wdir}  [{rama}]  destrucción={args.destruccion}")

        if cwd == principal and a.get("persist") and args.arbol != "rama_actual":
            pf_now = preflight(principal, cfg) or {}
            if pf_now.get("dirty", 0) > 0:
                print(f"  ❌ {key}: iba a correr en el árbol PRINCIPAL con dirty={pf_now['dirty']} "
                      f"(WIP ajeno). Usá --arbol worktree o --rama. No se lanza.")
                continue

        # headless (-p): resultado JSON parseable, pero INVISIBLE en remota.
        # visible (--bg): sale en `claude agents`, se puede `attach`/`logs`/`stop`,
        # pero no hay out.json — harvest tiene que leer los logs.
        # En --bg el prompt posicional se IGNORA: va por redirección de stdin.
        if args.visible:
            bgname = f"orq-{key}-{jid}"
            flags = [claude, "--bg", "--name", shlex.quote(bgname), *flags_add_dir]
        else:
            flags = [claude, "-p", "--output-format", "json", *flags_add_dir]
        if p["specialist"]:
            flags += ["--agent", p["specialist"]]
        if p.get("modelo"):        # el PLAN declara el modelo por task
            flags += ["--model", shlex.quote(p["modelo"])]
        flags += flags_tools(a)

        # Una sesión persistente se resume SOLO si todavía existe en la máquina.
        # Si se borró (claude rm, limpieza, otra máquina), `--resume <id-muerto>`
        # hace que la sesión muera al instante sin transcript y sin error claro:
        # se ve como "failed" y el id se repite corrida tras corrida.
        sid_previo = sesiones.get(key) if a["persist"] else None
        if sid_previo:
            _, ex, _ = remote(cfg, f"ls ~/.claude/projects/*/{shlex.quote(sid_previo)}.jsonl "
                                   f"2>/dev/null | head -1")
            if not ex.strip():
                print(f"  ⚠ {key}: la sesión previa {sid_previo[:8]} ya no existe en {HOST} "
                      f"→ se crea una nueva")
                sesiones.pop(key, None)
                sid_previo = None
        if sid_previo:
            flags += ["--resume", sid_previo]
        else:
            sid = str(uuid.uuid4())
            flags += ["--session-id", sid, "--name", f"orq-{key}"]
            if a["persist"]:
                sesiones[key] = sid

        jdir = rpath(cfg, f"~/.orq/jobs/{jid}")
        prompt = args.prompt or (
            f"Ejecutá TASK-{p['task']} de {t.get('plan_dir') or 'PLAN-' + p['plan']}.\n"
            f"Fuente de verdad: {planes}/{t.get('plan_dir')}/tasks/TASK-{p['task']}-*.md "
            f"y el master del plan (leé la sección `### Paralelismo`).\n"
            f"Trabajás en {cwd}, rama propia: commits ahí, conventional commits, SIN atribución "
            f"de AI, NUNCA push. No toques application*.properties.\n"
            f"Al cerrar: actualizá `Estado:` y llená `## Resultado` (Result Contract) del TASK "
            f"en {planes}/, con SHAs y archivos. Si algo bloquea, dejá `blocked` con el motivo "
            f"y pará." if p.get("plan") else t["intent"])
        # El comando va a un SCRIPT, no a `bash -c '...'`: los flags llevan
        # shlex.quote (p.ej. 'Bash(git *)') y las comillas simples anidadas se
        # cancelarían entre sí, dejando el comando roto y sin error visible.
        cmd = " ".join(flags)
        # El daemon de `--bg` NO sobrevive al cierre del SSH si queda en el grupo
        # de procesos de la sesión: hay que `setsid`, y ADEMÁS darle unos segundos
        # de gracia antes de que el ssh corte, o muere antes de levantar su socket
        # ("connect ENOENT /tmp/cc-daemon-*/control.sock"). Verificado: con setsid
        # + espera, la sesión sobrevive al cierre y termina sola.
        cabecera = f"""
mkdir -p {jdir}
cat > {jdir}/prompt.txt <<'ORQPROMPT'
{prompt}
ORQPROMPT
"""
        extraer_id = (f"sed 's/\\x1b\\[[0-9;]*[A-Za-z]//g' {jdir}/out.json 2>/dev/null "
                      f"| grep -oE 'backgrounded[^0-9a-f]+([0-9a-f]{{8}})' "
                      f"| grep -oE '[0-9a-f]{{8}}$' | head -1 > {jdir}/bgid")
        if args.visible:
            script = cabecera + f"""
cd {shlex.quote(cwd)} || exit 1
setsid nohup {cmd} < {jdir}/prompt.txt > {jdir}/out.json 2> {jdir}/err.log &
for i in $(seq 10); do sleep 1; grep -q backgrounded {jdir}/out.json 2>/dev/null && break; done
# El daemon es UNO por usuario: si la siguiente sesión arranca mientras éste
# todavía está levantando, se tumban entre sí y mueren las dos (daemons=0).
# Esperar a que el socket exista ANTES de soltar la conexión y lanzar la próxima.
for i in $(seq 20); do ls /tmp/cc-daemon-$(id -u)/*/control.sock >/dev/null 2>&1 && break; sleep 1; done
sleep 3
echo 0 > {jdir}/rc
{extraer_id}
grep -q . {jdir}/bgid && echo LANZADO {jid} || echo "FALLO: $(tail -2 {jdir}/err.log)"
"""
        else:
            script = cabecera + f"""
cat > {jdir}/run.sh <<'ORQRUN'
#!/bin/bash
cd {shlex.quote(cwd)} || exit 1
{cmd} < {jdir}/prompt.txt > {jdir}/out.json 2> {jdir}/err.log
echo $? > {jdir}/rc
ORQRUN
chmod +x {jdir}/run.sh
setsid nohup {jdir}/run.sh >/dev/null 2>&1 &
echo LANZADO {jid}
"""
        if os.environ.get("ORQ_DEBUG"):   # ORQ_DEBUG=1 imprime el script exacto:
            print("────── script enviado ──────\n" + script +   # fue lo que destapó
                  "────────────────────────────", file=sys.stderr)  # el --resume fantasma
        rc, out, err = remote(cfg, script, timeout=120)
        ok = "LANZADO" in out
        jobs[jid] = {"key": key, "ws": wsd["nombre"], "specialist": p["specialist"], "cwd": cwd,
                     "padre": padre, "lanzado": time.time(), "ok": ok,
                     "modo": "visible" if args.visible else "headless",
                     "bgname": bgname}
        lanzados.append((jid, key, p["specialist"], ok))
        print(f"  {'✅' if ok else '❌'} {key:<40} {p['specialist'] or 'general-purpose':<28} job={jid}")

    _save("sessions.json", sesiones)
    _save("jobs.json", jobs)
    _save("worktrees.json", wts)
    tp.unlink()   # token de un solo uso
    print(f"\n  {len(lanzados)} sesiones lanzadas. Orquestador: {padre}")
    print(f"  Seguimiento:  orq status   ·   orq logs <job>")
    return 0


# ─────────────────────── status / ls / tree ───────────────────────

def cmd_status(args):
    cfg = load_cfg()
    jobs = _load("jobs.json", {})
    if not jobs:
        print("  sin jobs registrados"); return 0
    ids = " ".join(jobs)
    rc, out, _ = remote(cfg, f"""
    for j in {ids}; do
      d=~/.orq/jobs/$j
      if [ -f $d/rc ]; then echo "$j FIN $(cat $d/rc)"
      elif [ -d $d ];  then echo "$j CORRIENDO -"
      else echo "$j PERDIDO -"; fi
    done""")
    vis = {}
    if any(m.get("modo") == "visible" for m in jobs.values()):
        _, aj, _ = remote(cfg, f"{maq(cfg)['claude']} agents --json --all 2>/dev/null")
        try:
            for a in json.loads(aj):
                vis[a.get("name") or ""] = (a.get("id"), a.get("state"))
        except Exception:
            pass

    print(f"\n  {'JOB':<10}{'WS':<18}{'SESIÓN':<40}{'SPECIALIST':<28}{'ESTADO'}")
    for line in out.splitlines():
        j, st, code = (line.split() + ["", ""])[:3]
        m = jobs.get(j, {})
        extra = f" (rc={code})" if st == "FIN" and code not in ("0", "-") else ""
        if m.get("modo") == "visible" and m.get("bgname") in vis:
            bid, bst = vis[m["bgname"]]
            # `attach` a una sesión TERMINADA la revive y, al salir, te deja una sesión
            # nueva en el cwd del login (~), que además pide confiar en esa carpeta.
            # Para las terminadas se usa `logs`, que no revive nada. Y el `cd` va
            # siempre: si igual cae en ese fallback, aterriza en el repo, no en ~.
            # Alias remota-tty = sin RemoteForward (el `remota` muere si el 2223 está tomado).
            viva = bst in ("working", "blocked", "awaiting_input")
            acc = (f"claude attach {bid}" if viva else f"claude logs {bid}")
            dentro = f"cd {m.get('cwd','~')} && ~/.local/bin/{acc}"
            st, extra = bst, (f"   {dentro}" if es_local(cfg)
                              else f"   ssh remota-tty '{dentro}'")
        print(f"  {j:<10}{corta(m.get('ws', cfg['workspace_default']),16):<18}"
              f"{corta(m.get('key',''),38):<40}"
              f"{corta(m.get('specialist') or '-',26):<28}{st}{extra}")
    print()
    return 0


def cmd_ls(args):
    cfg = load_cfg()
    ses = _load("sessions.json", {})
    if not ses:
        print("  sin sesiones vinculadas todavía"); return 0
    print(f"\n  {'WS':<18}{'SESIÓN':<40}{'SESSION-ID'}")
    for k, v in sorted(ses.items()):
        # sin prefijo `<ws>:` = clave anterior a los workspaces = el default
        ws_k, _, resto = k.partition(":")
        ws_k, k = (ws_k, resto) if resto and ws_k in cfg["workspaces"] else (cfg["workspace_default"], k)
        print(f"  {corta(ws_k,16):<18}{k:<40}{v}")
    print()
    return 0


def cmd_tree(args):
    jobs = _load("jobs.json", {})
    padres = {}
    for j, m in jobs.items():
        padres.setdefault(m.get("padre", "?"), []).append((j, m))
    for p, hijos in padres.items():
        print(f"\n  ORQUESTADOR {p}")
        for j, m in hijos:
            print(f"    └─ {m['key']:<38} {m.get('specialist') or '-':<26} job={j}")
    print()
    return 0


# ───────────────────────────── agent ─────────────────────────────

def cmd_agent_use(args):
    """Confirma un specialist para `arq@target` en el ws activo. Es el ÚNICO camino por el
    que un match pasa a escalón 1: orq propone, el usuario decide."""
    cfg = load_cfg()
    wsd = ws_actual(cfg)
    m = re.fullmatch(r"([\w-]+)@([^\s@]+)", args.destino)
    if not m:
        print(f"  destino `{args.destino}` inválido: se espera <arquetipo>@<target> "
              f"(target `*` = cualquiera)"); return 2
    arq, target = m.groups()
    if arq not in cfg["arquetipos"]:
        print(f"  arquetipo `{arq}` no existe. Declarados: {', '.join(cfg['arquetipos'])}"); return 2
    if target != "*":
        targets = descubrir_targets(cfg)
        if targets and target not in targets:
            print(f"  target `{target}` no existe en el ws `{wsd['nombre']}`. "
                  f"Targets: {', '.join(targets)}"); return 2
    cat = catalogo_agentes(cfg, None if target == "*" else target)
    ag = next((a for a in cat if a["name"] == args.nombre), None)
    if not ag:
        print(f"  el agente `{args.nombre}` no existe como .md alcanzable. Buscado en:")
        for d, _ in dirs_agentes(cfg, None if target == "*" else target):
            print(f"    · {d}")
        return 2
    ov = cargar_overlay()
    previo = ov.setdefault(wsd["nombre"], {}).get(args.destino)
    ov[wsd["nombre"]][args.destino] = args.nombre
    guardar_overlay(ov)
    print(f"  ✅ {wsd['nombre']}: {args.destino} → {args.nombre}  ({ag['path']})"
          + (f"\n     reemplaza a `{previo}`" if previo and previo != args.nombre else ""))
    return 0


# ───────────────────────────── scout (escalón 3, PLAN-001 DD-4) ─────────────────────────────

DRAFTS = STATE / "drafts"
SKILL_RECOMMENDER = "claude-code-setup:claude-automation-recommender"
TEMPLATES_RECOMMENDER = ("~/.claude/plugins/cache/claude-plugins-official/claude-code-setup/1.0.0/"
                         "skills/claude-automation-recommender/references/subagent-templates.md")
MODELOS_VALIDOS = ("sonnet", "opus", "haiku", "fable")


def repo_local(cfg, target):
    """Ruta LOCAL (local) del repo de un target: el scout siempre corre en local (tiene devctx)."""
    w = ws_actual(cfg)
    base = Path(expand(w["path"]))
    return base if w["tipo"] == "repo" else base / target


def dossier_scout(cfg, arq, target):
    """Lo MECÁNICO que orq ya sabe del repo, para que el scout no gaste turnos (ni plata) en
    redescubrirlo. Lo que requiere criterio (convenciones reales, stack) lo investiga él."""
    repo = repo_local(cfg, target)
    a = cfg["arquetipos"][arq]
    L = [f"Repo: {repo}", f"Señales de stack (por archivos marcadores): "
         f"{', '.join(señales_target(cfg, target)) or '(ninguna reconocida)'}"]
    for nombre in ("CLAUDE.md", "AGENTS.md"):
        f = repo / nombre
        if f.is_file():
            txt = f.read_text(errors="ignore")
            L.append(f"\n--- {nombre} (primeros 4000 caracteres) ---\n{txt[:4000]}")
    # el slug de ~/.claude/projects/ es la ruta con todo lo no alfanumérico convertido en `-`
    slug = re.sub(r"[^A-Za-z0-9]", "-", str(repo.resolve()))
    mem = Path.home() / ".claude" / "projects" / slug / "memory"
    nombres = sorted(x.name for x in mem.glob("*.md")) if mem.is_dir() else []
    L.append(f"\nMemoria de Claude de este repo ({mem}): "
             + (", ".join(nombres[:40]) if nombres else "(no existe)"))
    rc, log, _ = sh(["git", "-C", str(repo), "log", "--oneline", "-20"])
    L.append("\nÚltimos commits:\n" + (log if rc == 0 and log else "(sin historial)"))
    cat = catalogo_agentes(cfg, target)
    L.append("\nAgentes que YA existen y no hay que duplicar: "
             + ("; ".join(f"{x['name']} ({corta(x['description'], 70)})" for x in cat) or "(ninguno)"))
    L.append(f"\nPermisos del arquetipo `{arq}` (el agente debe declarar `tools:` acorde):\n"
             f"  tools: {', '.join(a['tools'])}\n"
             f"  disallowed: {', '.join(a.get('disallowed', [])) or '(ninguno)'}")
    return "\n".join(L)


def prompt_scout(cfg, arq, target):
    return f"""Sos un SCOUT: investigás un repo y diseñás UN agente (specialist) de Claude Code para el rol `{arq}` sobre `{target}`. NO tenés Write ni Edit y NO debés escribir archivos: tu entrega es el texto de tu respuesta final.

PASOS
1. Invocá la skill `{SKILL_RECOMMENDER}` y leé sus templates de subagentes en `{expand(TEMPLATES_RECOMMENDER)}`. Usalos como base de estructura, no los copies a ciegas.
2. Consultá la memoria del proyecto con `mcp__devctx__recall` y explorá el código con `mcp__devctx__search` / `mcp__devctx__build_context`: buscá convenciones, decisiones y gotchas REALES de este repo.
3. Con `mcp__context7__resolve-library-id` y `mcp__context7__query-docs` verificá las convenciones vigentes del stack que detectes.
4. Usá el dossier de abajo (ya está calculado) antes de volver a leer lo mismo.

REQUISITOS DEL AGENTE
- Frontmatter YAML con `name` (kebab-case), `description` (cuándo usarlo, concreto), `model` (OBLIGATORIO y fijado: uno de {', '.join(MODELOS_VALIDOS)}) y `tools` acorde al arquetipo `{arq}`.
- Cuerpo en español: rol, convenciones y comandos propios de ESTE repo, y qué NO debe hacer. Todo respaldado por evidencia que viste; si no lo viste, no lo afirmes.
- UN único agente. No propongas hooks, skills ni MCPs.

FORMATO DE SALIDA (obligatorio, sin nada dentro de los marcadores que no sea el contenido pedido)
<<<AGENTE
---
name: ...
description: ...
model: ...
tools: ...
---
(cuerpo del agente)
AGENTE>>>
<<<RAZONES
(por qué este agente: qué archivos, memorias y docs lo respaldan; máximo 15 líneas)
RAZONES>>>

DOSSIER
{dossier_scout(cfg, arq, target)}
"""


def _extraer(marca, texto):
    m = re.search(rf"<<<{marca}[ \t]*\n(.*?)\n{marca}>>>", texto, re.S)
    return m.group(1).strip("\n") if m else None


def cmd_scout(args):
    cfg = load_cfg()
    if not args.token:
        print("`orq scout` gasta tokens y necesita aval: corré `orq need` (propone los scouts "
              "con su costo) y pasá su token: orq scout --token T-… [--only N]", file=sys.stderr)
        return 2
    tp = STATE / "tokens" / f"{args.token}.json"
    if not tp.exists():
        print(f"token {args.token} inválido o ya usado. Corré `orq need` primero.", file=sys.stderr)
        return 2
    t = json.loads(tp.read_text())
    if time.time() - t["emitido"] > TOKEN_TTL:
        tp.unlink()
        print("token vencido. Corré `orq need` de nuevo.", file=sys.stderr)
        return 2
    global WS_NOMBRE
    if t.get("ws"):
        WS_NOMBRE = t["ws"]
    scouts = t.get("scouts") or []
    if not scouts:
        print("este token no propone scouts (todo faltante tiene candidatos o specialist).", file=sys.stderr)
        return 2
    if args.destino:
        ix = [i for i, s_ in enumerate(scouts, 1) if s_["clave"] == args.destino]
    elif args.only:
        ix = [int(x) for x in args.only.split(",") if x.strip().isdigit()]
    else:
        ix = [1] if len(scouts) == 1 else []
    if len(ix) != 1 or not 1 <= ix[0] <= len(scouts):
        print("elegí UN scout con --only N (o pasando <arq>@<target>):", file=sys.stderr)
        for i, s_ in enumerate(scouts, 1):
            print(f"  S{i} {s_['clave']}", file=sys.stderr)
        return 2
    sel = scouts[ix[0] - 1]
    if sel.get("hecho"):
        print(f"el scout {sel['clave']} ya corrió con este token (costó plata). "
              f"Para repetirlo, `orq need` de nuevo.", file=sys.stderr)
        return 2

    arq, target, clave = sel["arquetipo"], sel["target"], sel["clave"]
    sc = cfg["arquetipos"]["scout"]
    claude = expand(bin_claude(cfg, sc["maquina"]))
    if not (os.path.isfile(claude) and os.access(claude, os.X_OK)):
        print(f"no encuentro el binario de claude en {claude}", file=sys.stderr)
        return 1
    repo = repo_local(cfg, target)
    if not repo.is_dir():
        print(f"el repo {repo} no existe en esta máquina", file=sys.stderr)
        return 1

    jid = secrets.token_hex(4)
    jdir = STATE / "jobs" / jid
    jdir.mkdir(parents=True, exist_ok=True)
    (jdir / "prompt.txt").write_text(prompt_scout(cfg, arq, target))
    cmd = [claude, "-p", "--output-format", "json", "--model", sc["modelo"],
           "--name", f"orq-scout-{clave}", *flags_tools(sc, quote=False)]
    # se marca ANTES de correr: si el scout falla igual costó, y reintentar sin avisar es gastar doble
    sel["hecho"] = time.time()
    tp.write_text(json.dumps(t, indent=2, ensure_ascii=False))
    print(f"  🔎 scout {clave} · job {jid} · modelo {sc['modelo']} · máx {sc['timeout']}s …")
    out_json = jdir / "out.json"
    try:
        with open(jdir / "prompt.txt") as fin, open(out_json, "w") as fo, open(jdir / "err.log", "w") as fe:
            r = subprocess.run(cmd, cwd=str(repo), stdin=fin, stdout=fo, stderr=fe,
                               timeout=sc["timeout"])
    except subprocess.TimeoutExpired:
        print(f"  ❌ el scout superó {sc['timeout']}s. Salida parcial: {out_json}", file=sys.stderr)
        return 1
    try:
        d = json.loads(out_json.read_text())
    except Exception:
        print(f"  ❌ rc={r.returncode} y out.json no es JSON. Ver {out_json} y {jdir}/err.log",
              file=sys.stderr)
        return 1
    # una sesión que falla (permisos, límite de uso) puede venir SIN `result`: se dice por qué
    if d.get("is_error") or d.get("subtype", "success") != "success":
        print(f"  ❌ el scout falló: subtype={d.get('subtype')} is_error={d.get('is_error')} "
              f"{corta(str(d.get('result', '')), 200)}\n     Detalle: {out_json}", file=sys.stderr)
        return 1
    texto = d.get("result") or ""
    agente, razones = _extraer("AGENTE", texto), _extraer("RAZONES", texto)
    if not agente:
        print(f"  ❌ el scout no devolvió el bloque <<<AGENTE … AGENTE>>>. No se escribe ningún "
              f"draft. Respuesta completa en {out_json}", file=sys.stderr)
        return 1
    fm = parse_frontmatter(agente)
    nombre = fm.get("name", "")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", nombre):
        print(f"  ❌ el agente devuelto no tiene un `name` válido en el frontmatter "
              f"({nombre!r}). Respuesta en {out_json}", file=sys.stderr)
        return 1
    DRAFTS.mkdir(parents=True, exist_ok=True)
    draft = DRAFTS / f"{nombre}.md"
    previo = draft.exists()
    draft.write_text(agente.rstrip("\n") + "\n")
    rz = DRAFTS / f"{nombre}.razones.md"
    rz.write_text((razones or "(el scout no devolvió bloque RAZONES)").rstrip("\n") + "\n")

    print(f"\n  ✅ draft{' (reemplaza al anterior)' if previo else ''}: {draft}")
    print(f"     razones: {rz}")
    for ln in (razones or "(sin RAZONES)").splitlines()[:10]:
        print(f"       {ln}")
    if fm.get("model") not in MODELOS_VALIDOS:
        print(f"  ⚠ el draft NO fija `model:` válido ({fm.get('model') or 'falta'}): `agent save` lo "
              f"va a rechazar; editá el draft antes.")
    print("\n  Revisalo y elegí DÓNDE guardarlo (el scope lo decide el usuario, no hay default):")
    for l in texto_scopes(cfg):
        print(l)
    print(f"\n  orq agent save {draft} {clave} --scope ?     (p | m | g)\n")
    return 0


# ───────────────────────────── harvest ─────────────────────────────

def ws_plans(cfg):
    """Dir de PLANs del workspace activo (se leen LOCAL: harvest/plan corren en local)."""
    return Path(expand(ws_actual(cfg)["plans"]))


def ws_agents(cfg):
    """Dir de agentes del workspace activo (local)."""
    return Path(expand(ws_actual(cfg)["agents"]))


# 25+ variantes reales -> 5. Se normaliza, nunca se confía en el string crudo.
def primer_valor(v):
    """El campo trae prosa pegada: '✅ **`done`** — ejecutada en REMOTA contra...'.
    Nos quedamos con el primer token entre backticks; si no hay, la primera palabra."""
    v = (v or "").split("—")[0].split(" - ")[0]
    m = re.search(r"`([^`]+)`", v)
    if m:
        return m.group(1).strip()
    v = re.sub(r"[*_~#✅🔴🟢🟤🟩⚠️🆕🧭]", " ", v).strip()
    return (v.split() or [""])[0].strip(".,;:")


def norm_estado(v, cfg):
    v = primer_valor(v).strip("`*_ ").lower()
    for canon, variantes in cfg["normalizar_estado"].items():
        if v in {x.lower() for x in variantes} or v == canon:
            return canon
    return f"?{v}" if v else "?vacio"


CAMPO = lambda t, n: (re.search(rf"^\s*-\s*\*\*{n}:\*\*\s*(.+)$", t, re.M | re.I) or [None, ""])[1].strip()


def parse_task(path, cfg):
    full = path.read_text(errors="ignore")
    t = full[:3000]                 # la cabecera con los campos vive arriba
    # OJO: el Result Contract va al FINAL del archivo. Chequearlo contra `t`
    # (los primeros 3000 chars) marcaba como vacío TODO lo que no cupiera ahí.
    mres = re.search(r"##\s*Resultado(.*)$", full, re.S)
    cuerpo = mres.group(1) if mres else ""
    lleno = len(re.sub(r"(?i)[\s\-*:>|]|estado final|resumen|archivos tocados|"
                       r"verificado por|desviaciones|riesgos abiertos", "", cuerpo)) > 80
    deps_raw = CAMPO(t, "Depende de")
    # IDs limpios que sí se pueden usar; el resto queda como prosa a leer
    ids = re.findall(r"\b0*(\d{1,3})\b", deps_raw.split("(")[0]) if deps_raw not in ("—", "-", "") else []
    return {
        "id": (re.search(r"TASK-(\d+)", path.name) or ["", "?"])[1],
        "titulo": (re.search(r"^#\s*(.+)$", t, re.M) or ["", path.stem])[1][:70],
        "especialista": CAMPO(t, "Especialista") or CAMPO(t, "Specialist"),
        "modelo": CAMPO(t, "Modelo") or CAMPO(t, "Model"),
        "proyecto": CAMPO(t, "Proyecto") or CAMPO(t, "Project"),
        "deps_raw": deps_raw, "deps": sorted(set(ids)),
        "deps_ambiguo": bool(re.search(r"[·+]|\bsi\b|\bP\d|PLAN-", deps_raw, re.I)),
        "estado": norm_estado(CAMPO(t, "Estado") or CAMPO(t, "Status"), cfg),
        "resultado_lleno": lleno,
        "path": str(path),
    }


def primer_nombre(v):
    """El nombre del specialist es la primera palabra DESNUDA, no el primer backtick.
    En el campo Especialista el backtick puede ser el modelo —`workspace-architect
    (`opus`)`— o una referencia —`... según se resuelva `DP-7``—. Mismo patrón que
    el campo Proyecto, donde el primer backtick era la ruta y no el repo."""
    v = re.sub(r"\*\*", "", (v or "")).strip()
    m = re.match(r"\s*`?([A-Za-z][\w.-]*)`?", v)
    return m.group(1) if m else ""


def repo_y_rama(proyecto):
    """`api-backend (`/ruta/`), rama `feature/x` (worktree desde `gitlab/staging`)`
    → ('api-backend', 'feature/x', 'gitlab/staging'). El repo es la primera palabra
    DESNUDA, no el primer backtick (ese es la ruta absoluta)."""
    txt = re.sub(r"\*\*", "", proyecto or "")
    repo = (re.match(r"\s*`?([A-Za-z][\w.-]+)`?", txt) or ["", ""])[1]
    rama = (re.search(r"rama\s+`([^`]+)`", txt) or ["", ""])[1]
    base = (re.search(r"desde\s+`([^`]+)`", txt) or ["", ""])[1]
    return repo, rama, base


def modelos_del_master(master):
    """El `Modelo` por task vive en la tabla del master, no en el archivo de la task."""
    out = {}
    if master and master.exists():
        for fila in re.findall(r"^\|\s*\*\*TASK-(\d+)\*\*\s*\|(.+)$", master.read_text(errors="ignore"), re.M):
            tid, resto = fila
            cols = [c.strip().strip("`*") for c in resto.split("|")]
            mod = next((c for c in cols if c.lower() in ("opus", "sonnet", "haiku", "fable")), "")
            if mod:
                out[tid.lstrip("0")] = mod.lower()
    return out


def cargar_plan(numero, cfg):
    """Devuelve (pdir, master, tasks, lotes) de un PLAN. Compartido por `plan` y `need`."""
    cands = sorted(ws_plans(cfg).glob(f"PLAN-{int(numero):03d}*"))
    if not cands:
        return None, None, [], []
    pdir = cands[0]
    master = pdir / f"{pdir.name}.md"
    if not master.exists():
        master = next((f for f in sorted(pdir.glob("PLAN-*.md"))
                       if not re.search(r"-(design|resumen|notas)\.md$", f.name)), None)
    tasks = [parse_task(f, cfg) for f in sorted((pdir / "tasks").glob("TASK-*.md"))]
    lotes = []
    if master:
        sec = re.search(r"#+\s*Paralelismo(.*?)(?=\n#{2,3}\s|\Z)", master.read_text(errors="ignore"), re.S)
        if sec:
            for lote, cont in re.findall(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", sec.group(1), re.M):
                if set(lote) <= set("-: |") or lote.lower().startswith("lote"):
                    continue
                ids, vistos = [], set()
                for grupo in re.findall(r"\*\*([^*]+)\*\*", cont):
                    for n in re.findall(r"\b(\d{2,3})\b", grupo):
                        if n not in vistos:
                            vistos.add(n); ids.append(n)
                lotes.append((re.sub(r"[*~]", "", lote).strip(), ids, cont))
    return pdir, master, tasks, lotes


def propuesta_de_lote(numero, lote_pedido, cfg):
    """Una sesión por TASK del lote, con el specialist y el modelo que el PLAN declara."""
    pdir, master, tasks, lotes = cargar_plan(numero, cfg)
    if not pdir:
        return None, f"no encontré PLAN-{numero}"
    match = next((l for l in lotes if l[0].split()[0].strip("*` ") == str(lote_pedido)), None)
    if not match:
        return None, (f"el lote `{lote_pedido}` no está en el master. Lotes: "
                      + ", ".join(l[0] for l in lotes) if lotes else
                      "el master no tiene sección `### Paralelismo`")
    _, ids, cont = match
    mods = modelos_del_master(master)
    por_repo, prop, saltadas = {}, [], []
    for tid in ids:
        t = next((x for x in tasks if x["id"].lstrip("0") == tid.lstrip("0")), None)
        if not t:
            continue
        if t["estado"] in ("done", "skipped"):
            saltadas.append(f"TASK-{t['id']} ({t['estado']})"); continue
        repo, rama, base = repo_y_rama(t["proyecto"])
        por_repo[repo] = por_repo.get(repo, 0) + 1
        prop.append({"task": t["id"], "titulo": t["titulo"], "target": repo,
                     "specialist": primer_nombre(t["especialista"]),
                     "modelo": mods.get(t["id"].lstrip("0")) or primer_valor(t["modelo"]) or "sonnet",
                     "rama_plan": rama, "base_plan": base,
                     "arquetipo": "worker", "estado": "crear", "deps_raw": t["deps_raw"],
                     "plan": str(numero), "modo": "implementar",
                     "pregunta": f"implementar TASK-{t['id']}: ¿rama actual / otra / worktree?"})
    return {"prop": prop, "por_repo": por_repo, "saltadas": saltadas,
            "pdir_nombre": pdir.name,
            "ramas": sorted({p["rama_plan"] for p in prop if p.get("rama_plan")}),
            "bases": sorted({p["base_plan"] for p in prop if p.get("base_plan")}),
            "condicion": cont, "lote": match[0]}, None


def cmd_plan(args):
    """Lee un PLAN real: olas declaradas, specialists que pide, estados normalizados.

    NO infiere el DAG. Las dependencias son prosa con condicionales y sub-pasos;
    se muestra lo que se puede parsear y se marca lo ambiguo para que lo lea el usuario.
    """
    cfg = load_cfg()
    cands = sorted(ws_plans(cfg).glob(f"PLAN-{int(args.numero):03d}*"))
    if not cands:
        print(f"  no encontré PLAN-{args.numero} en {ws_plans(cfg)}"); return 1
    pdir = cands[0]
    # El master se llama IGUAL que la carpeta. `sorted()` agarraría PLAN-N-design.md.
    master = pdir / f"{pdir.name}.md"
    if not master.exists():
        master = next((f for f in sorted(pdir.glob("PLAN-*.md"))
                       if not re.search(r"-(design|resumen|notas)\.md$", f.name)), None)
    tasks = [parse_task(f, cfg) for f in sorted((pdir / "tasks").glob("TASK-*.md"))]
    print(f"\n  {pdir.name}  —  {len(tasks)} tasks\n")

    # ── olas declaradas a mano (el artefacto que el orquestador QUIERE) ──
    lotes = []
    if master:
        sec = re.search(r"#+\s*Paralelismo(.*?)(?=\n#{2,3}\s|\Z)", master.read_text(errors="ignore"), re.S)
        if sec:
            for row in re.findall(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", sec.group(1), re.M):
                lote, cont = row
                if set(lote) <= set("-: |") or lote.lower().startswith("lote"):
                    continue
                # `**004, 005, 009**` es UN grupo en negrita con varios números:
                # hay que sacar todos los de adentro, no solo el primero. Y dedup
                # conservando el orden (018 A y 018 C son la misma task, dos partes).
                ids, vistos = [], set()
                for grupo in re.findall(r"\*\*([^*]+)\*\*", cont):
                    for n in re.findall(r"\b(\d{2,3})\b", grupo):
                        if n not in vistos:
                            vistos.add(n); ids.append(n)
                lotes.append((re.sub(r"[*~]", "", lote).strip(), ids, cont))

    if lotes:
        print("  ✅ OLAS DECLARADAS en el master (se usan tal cual, no se infieren):\n")
        for lote, ids, cont in lotes:
            hechas = [i for i in ids if next((t for t in tasks if t["id"].lstrip("0") == i.lstrip("0")
                                              and t["estado"] == "done"), None)]
            print(f"    Lote {lote:<16} tasks: {', '.join(ids) or '—'}"
                  f"{'   (done: ' + ','.join(hechas) + ')' if hechas else ''}")
        print("\n    Las condiciones de desbloqueo son PROSA: leelas en el master antes de lanzar.")
    else:
        print("  ⚠ El master NO tiene sección `### Paralelismo`.")
        print("    Hay que PROPONER las olas y que el usuario las apruebe;")
        print("    lo aprobado se escribe al master para que la próxima se lea directo.")

    # ── estados ──
    from collections import Counter
    c = Counter(t["estado"] for t in tasks)
    print(f"\n  ESTADOS (normalizados): " + " · ".join(f"{k}={v}" for k, v in sorted(c.items())))
    mentira = [t for t in tasks if t["estado"] == "done" and not t["resultado_lleno"]]
    if mentira:
        print(f"  ⚠ {len(mentira)} de {c.get('done',0)} tasks en `done` SIN Result Contract lleno:")
        print(f"    {', '.join('TASK-'+t['id'] for t in mentira[:14])}")
        print("    `done` NO libera dependientes: verificá contra git antes de arrancar lo que sigue.")

    # ── specialists que el PLAN pide ──
    # el repo de la task decide qué agentes de proyecto se ven; el nombre está bien si algún
    # repo del plan lo alcanza
    repos_plan = {repo_y_rama(t["proyecto"])[0] or None for t in tasks} or {None}
    cats = [{a["name"]: a for a in catalogo_agentes(cfg, r)} for r in repos_plan]
    pedidos = Counter(primer_nombre(t["especialista"]) for t in tasks if t["especialista"])
    repo_de = {}
    for t in tasks:
        repo_de.setdefault(primer_nombre(t["especialista"]), repo_y_rama(t["proyecto"])[0])
    scope_txt = {"p": "proyecto", "m": "monorepo", "g": "global"}
    print(f"\n  SPECIALISTS QUE PIDE EL PLAN:")
    faltan = []
    for sp, n in pedidos.most_common():
        sp_clean = sp
        hallado = next((c[sp_clean] for c in cats if sp_clean in c), None)
        ok = hallado is not None
        print(f"    {'✅' if ok else '❌'} {sp_clean:<34} {n:>3} tasks   "
              f"ORIGEN {scope_txt[hallado['scope']] if ok else '-'}")
        if not ok:
            faltan.append(sp_clean)
    if faltan:
        print(f"\n  ❌ El plan nombra specialists que NO existen: {', '.join(faltan)}")
        print("     Proponé su estructura (devctx + memoria histórica + context7) y")
        print("     PREGUNTÁ el scope: [p] proyecto  "
              + ("" if ws_actual(cfg)["tipo"] == "repo" else "[m] monorepo  ") + "[g] global")
        for n in faltan:
            r = repo_de.get(n) or ws_actual(cfg)["nombre"]
            rs = resolver_specialist("worker", r, cfg)
            rs["aviso"] = None
            print(f"    · {n}")
            for l in lineas_candidatos(f"worker@{r}", rs):
                print(l)

    amb = [t for t in tasks if t["deps_ambiguo"]]
    if amb:
        print(f"\n  ⚠ {len(amb)} tasks con `Depende de` NO parseable (condicionales, sub-pasos,")
        print(f"    referencias a otros PLAN). No se infiere el orden de estas:")
        for t in amb[:6]:
            print(f"      TASK-{t['id']}: {t['deps_raw'][:88]}")
    print()
    return 0


_EXTRAER = r"""
f=$(ls ~/.claude/projects/*/%s*.jsonl 2>/dev/null | head -1)
[ -n "$f" ] || exit 0
python3 - "$f" <<'ORQPY'
import json, sys
ult = ""
for linea in open(sys.argv[1], errors="ignore"):
    try:
        d = json.loads(linea)
    except Exception:
        continue
    if d.get("type") != "assistant":
        continue
    for b in (d.get("message") or {}).get("content") or []:
        if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
            ult = b["text"]
print(ult)
ORQPY
"""


def cmd_harvest(args):
    """Cosecha resultados y los convierte en pending-agent-updates.json REAL.

    El hook nativo de SessionEnd solo escribe un marcador vacío (sin `agents`),
    y encima solo si el archivo no existe — por eso lleva meses estancado.
    remota no tiene devctx: esta es la ÚNICA vía de vuelta de los aprendizajes.
    """
    cfg = load_cfg()
    jobs = _load("jobs.json", {})
    pend = Path.home() / ".claude" / "pending-agent-updates.json"
    prev = json.loads(pend.read_text()) if pend.exists() else {}
    agentes = prev.get("agents", {})
    cosechados = 0

    for j, m in jobs.items():
        if m.get("cosechado"):
            continue
        if m.get("modo") == "visible":
            # --bg no deja out.json con JSON: el resultado se saca del transcript
            # de la sesión, que es limpio. `claude logs` daría la TUI con escapes ANSI.
            _, bid, _ = remote(cfg, "cat ~/.orq/jobs/%s/bgid 2>/dev/null" % j)
            if not bid.strip():
                continue
            _, res, _ = remote(cfg, _EXTRAER % bid.strip())
            res = res.strip()
        else:
            _, out, _ = remote(cfg, "[ -f ~/.orq/jobs/%s/out.json ] && cat ~/.orq/jobs/%s/out.json" % (j, j))
            if not out:
                continue
            try:
                res = json.loads(out).get("result", "")
            except json.JSONDecodeError:
                continue
        if len(res.strip()) < 60:
            # un SHA suelto o un "OK" no es un aprendizaje: no ensucia al agente
            m["cosechado"] = True
            continue
        sp = m.get("specialist")
        if sp and res:
            agentes.setdefault(sp, {"gotchas": [], "proven_patterns": []})
            agentes[sp]["proven_patterns"].append(
                {"from_job": j, "session": m["key"], "text": res[:1500]})
            cosechados += 1
        m["cosechado"] = True

    _save("jobs.json", jobs)
    pend.write_text(json.dumps(
        {"needs_review": True, "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
         "source": "orq-harvest", "agents": agentes}, indent=2, ensure_ascii=False))
    print(f"  cosechados {cosechados} resultados → {pend}")
    print(f"  agentes afectados: {', '.join(agentes) or 'ninguno'}")
    print("  siguiente paso:  /agent-evolve   (presenta los cambios antes de escribir)")
    return 0


def cmd_reap(args):
    """Lista worktrees y jobs zombie. NO borra nada sin --force."""
    cfg = load_cfg()
    wts = _load("worktrees.json", {})
    jobs = _load("jobs.json", {})

    zombis = [j for j, m in jobs.items() if not m.get("ok")]
    if zombis:
        print(f"\n  JOBS ZOMBIE (nunca arrancaron): {', '.join(zombis)}")
        if args.force:
            for j in zombis:
                jobs.pop(j, None)
            _save("jobs.json", jobs)
            print("  → eliminados del registro")

    if not wts:
        print("\n  sin worktrees registrados\n")
        return 0

    print(f"\n  {'WORKTREE':<52}{'WS':<18}{'RAMA':<30}{'DESTRUCCIÓN':<12}{'ESTADO'}")
    for w, m in wts.items():
        _, out, _ = remote(cfg, f"[ -d {shlex.quote(w)} ] && "
                                f"git -C {shlex.quote(w)} status --porcelain | wc -l || echo NOEXISTE")
        estado = "NO EXISTE" if "NOEXISTE" in out else f"dirty={out.strip()}"
        # el registro tiene dos formas: una sesión (per-task) o varias (worktree compartido)
        ses = m.get("sesiones") or ([m["sesion"]] if m.get("sesion") else [])
        print(f"  {corta(w,50):<52}{corta(m.get('ws', cfg['workspace_default']),16):<18}"
              f"{corta(m.get('rama','?'),28):<30}"
              f"{str(m.get('destruccion','?')):<12}{estado}")
        if ses:
            print(f"      sesiones: {', '.join(ses)}")
    print("\n  Nada se borra solo. Para eliminar uno:")
    rm = "git -C <repo-principal> worktree remove <ruta>"
    print(f"    {rm}\n" if es_local(load_cfg()) else f"    ssh remota '{rm}'\n")
    return 0


# ───────────────────────────── main ─────────────────────────────

def main():
    ap = argparse.ArgumentParser(prog="orq", description="orquestador de sesiones Claude")
    ap.add_argument("--host", choices=["local", "remota"],
                    help="dónde corren las sesiones (default: ORQ_HOST o local)")
    ap.add_argument("--ws", help="workspace declarado en roles.py (default: el que contiene "
                                 "el cwd, si no workspace_default)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("need", help="resolver qué sesiones hacen falta y emitir token")
    n.add_argument("intent", nargs="?", default="")
    n.add_argument("--plan", help="número de PLAN; propone desde un lote declarado")
    n.add_argument("--lote", default="0", help="lote del plan (default 0)")
    n.add_argument("--paralelo", type=int, default=1,
                   help="cuántas tareas simultáneas por repo (>1 => worktree por tarea)")
    n.set_defaults(fn=cmd_need)

    s = sub.add_parser("spawn", help="levantar las sesiones aprobadas (requiere token)")
    s.add_argument("--token", required=True); s.add_argument("--prompt")
    s.add_argument("--only", help="solo estas filas de la propuesta, ej: 2 o 1,3")
    s.add_argument("--arbol", help="rama_actual | otra:<nombre> | worktree")
    s.add_argument("--rama", help="worktree COMPARTIDO por repo con esta rama (lo reusa si existe)")
    s.add_argument("--base", help="base del worktree, ej gitlab/staging (hace fetch antes)")
    s.add_argument("--visible", action="store_true",
                   help="sesiones con --bg: salen en `claude agents` de remota y se les puede attach")
    s.add_argument("--destruccion", choices=["nunca", "si_limpio", "tras_merge"],
                   help="política de destrucción de los worktrees que se creen")
    s.set_defaults(fn=cmd_spawn)

    for name, fn, h in (("status", cmd_status, "estado de los jobs"),
                        ("ls", cmd_ls, "sesiones vinculadas"),
                        ("tree", cmd_tree, "jerarquía orquestador → hijas"),
                        ("harvest", cmd_harvest, "cosechar resultados para /agent-evolve")):
        p = sub.add_parser(name, help=h); p.set_defaults(fn=fn)

    pl = sub.add_parser("plan", help="leer un PLAN: olas, estados, specialists que pide")
    pl.add_argument("numero"); pl.set_defaults(fn=cmd_plan)

    ag = sub.add_parser("agent", help="gestionar los specialists del workspace")
    ags = ag.add_subparsers(dest="agente_cmd", required=True)
    u = ags.add_parser("use", help="confirmar un agente existente para <arquetipo>@<target>")
    u.add_argument("nombre"); u.add_argument("destino", help="<arquetipo>@<target> (target * = todos)")
    u.set_defaults(fn=cmd_agent_use)
    sc = sub.add_parser("scout", help="investigar un repo y dejar un draft de agente (cuesta; pide token)")
    sc.add_argument("destino", nargs="?", help="<arquetipo>@<target> del scout propuesto en el token")
    sc.add_argument("--token"); sc.add_argument("--only", help="N del scout a correr (S1, S2…)")
    sc.set_defaults(fn=cmd_scout)

    r = sub.add_parser("reap", help="listar worktrees y jobs zombie (no borra solo)")
    r.add_argument("--force", action="store_true", help="limpiar jobs zombie del registro")
    r.set_defaults(fn=cmd_reap)

    args = ap.parse_args()
    global HOST
    if args.host:
        HOST = args.host
    global WS_NOMBRE
    WS_NOMBRE = resolver_ws(args.ws, load_cfg())
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
