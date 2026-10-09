# PLAN-001 — Diseño

## DD-1 — Workspaces declarados en `roles.py`
```python
"workspaces": {
    "mi-empresa":            {"path": "~/proyectos/mi-empresa", "tipo": "multi",
                         "add_dir": "~/proyectos/mi-empresa",                 # el trap verificado sigue vigente
                         "agents": "~/proyectos/mi-empresa/.claude/agents", "plans": "~/proyectos/mi-empresa/plans",
                         "ruido": ["mi-empresa","api","backend",...]},
    "herramienta": {"path": "~/personal/herramienta", "tipo": "repo"},
},
"workspace_default": "mi-empresa",
```
- `multi`: targets = subdirectorios con `.git` (comportamiento actual de `descubrir_targets`).
- `repo`: el target es el propio repo; `agents` = `<repo>/.claude/agents`, `plans` = `<repo>/plans`,
  **sin** `--add-dir` (el agente de proyecto resuelve por cwd).
- Selección: `--ws <nombre>` → si no, el workspace cuyo `path` contiene el cwd → si no, `workspace_default`.
- `maquinas.*.workspace` se elimina; `PLANS`/`AGENTS_DIR` globales pasan a funciones `ws_plans(ws)`/`ws_agents(ws)`.
- **Regla dura**: con `--ws mi-empresa` la salida de `need`/`plan` tiene que ser idéntica a la de hoy (TASK-006).

## DD-2 — Resolución en 3 escalones (decidido con el usuario 2026-10-08)
```
1. CONFIRMADO   ~/.orq/specialists.json → roles.py["specialists"]        → se usa
2. MATCH        agentes en disco con afinidad ≥ umbral                    → se PROPONEN, el usuario confirma
3. SCOUT        ninguno sirve                                             → se propone investigar (cuesta), el usuario avala
```
- Escalón 1 verifica que el nombre mapeado **exista como `.md`** en un dir alcanzable con los flags
  de spawn. Mapeado-pero-inexistente = faltante (hoy cae a genérico en silencio).
- Todo lo que el usuario confirma (match o save) se escribe en `specialists.json` → la próxima vez es escalón 1.

## DD-3 — Match por afinidad (escalón 2), mecánico y determinístico
- **Catálogo**: frontmatter (`name`, `description`, `model`, `tools`) de cada `.md` en
  `<repo>/.claude/agents`, `ws_agents(ws)` y `~/.claude/agents`. Parser de frontmatter a mano
  (stdlib, sin yaml: este python no tiene pip).
- **Señales del target**: archivos marcadores → tags de stack. Tabla en `roles.py["señales"]`:
  `pom.xml|build.gradle → java`, `quarkus` en pom → `quarkus`, `angular.json → angular`,
  `nx.json → nx`, `go.mod → go`, `Cargo.toml → rust`, `pyproject.toml|requirements.txt → python`,
  `package.json → node`, más el arquetipo (`reviewer` ↔ "review|audit").
- **Puntaje** = tags del target encontrados en `description`+`name` del agente / tags del target,
  con bonus si el agente ya está mapeado para otro target del mismo ws. Umbral en `roles.py`
  (`match_umbral`, arranque 0.5). Se muestran top 3 con los tags que matchearon:
  `java-backend-specialist  0.83  [java, quarkus, oracle]`.
- **Nunca se autoasigna.** Confirmación: `orq agent use <nombre> <arq>@<target>`.

## DD-4 — Scout (escalón 3): orq lanza la investigación
`orq.py` no puede usar skills ni MCPs; **una sesión `claude -p` sí**. El scout es un arquetipo:
```python
"scout": {"descripcion": "investiga el repo y propone un agente",
          "tools": ["Read","Grep","Glob","Bash(git log*)","Bash(ls*)","Skill",
                    "mcp__devctx__search","mcp__devctx__recall","mcp__devctx__build_context",
                    "mcp__context7__resolve-library-id","mcp__context7__query-docs"],
          "disallowed": ["Write","Edit"], "persist": False, "modelo": "sonnet",
          "maquina": "local"}   # una máquina remota no tiene devctx
```
- `orq scout <arq>@<target> [--ws]` → **pide token como spawn** (regla de oro): `need` lo propone
  con costo estimado; `orq scout --token T-…` lo ejecuta.
- Prompt del scout: dossier mecánico (señales, CLAUDE.md, nombres de `~/.claude/projects/<slug>/memory/`,
  últimos 20 commits, tools del arquetipo pedido) + instrucciones: usar la skill
  `claude-code-setup:claude-automation-recommender` (templates en `references/subagent-templates.md`),
  `recall`/`search` de devctx y context7 del stack; devolver **un único agente** entre marcadores
  `<<<AGENTE` … `AGENTE>>>` + un bloque `<<<RAZONES` con evidencia.
- orq corre `claude -p --output-format json` en foreground (timeout 10 min), extrae los marcadores
  del campo `result` y escribe `~/.orq/drafts/<nombre>.md` + `<nombre>.razones.md`.
  Si no hay marcadores → error con la ruta del `out.json`, no un draft vacío.
- El scout **no escribe nada**: el draft lo escribe orq, el agente lo escribe `save`.

## DD-5 — Guardar: el scope SE PREGUNTA SIEMPRE
`orq agent save <draft> --scope p|m|g` — sin `--scope` → rc=2. Nunca hay default.

| ws | Scopes ofrecidos |
|---|---|
| `multi` | `[p]` `<repo>/.claude/agents` · `[m]` `ws.agents` (exige `add_dir`) · `[g]` `~/.claude/agents` |
| `repo` | `[p]` `<repo>/.claude/agents` · `[g]` `~/.claude/agents` |

Valida: `name`, `description`, `model` ∈ sonnet|opus|haiku|fable (**obligatorio**, regla global),
no pisa un archivo existente sin `--force`. Registra en `specialists.json`.

## DD-6 — Spawn ya no es silencioso
`cmd_spawn` sale rc=2 si alguna sesión del token no tiene specialist, salvo `--sin-specialist N,M`
(aceptación por sesión, queda en el token). Re-resuelve antes de lanzar: si entre `need` y `spawn`
se confirmó un match o se guardó un agente, se usa sin pedir flag.

## DD-7 — Alternativas descartadas
- Skill `proponer-agente` separada: hoy el único consumidor es orq. Se extrae si aparece otro.
- Capa automática de agentes genéricos globales: descartada por el usuario. Un agente de stack
  global puede existir, pero solo si el usuario elige `[g]` al guardarlo.
- Match semántico con LLM: el puntaje mecánico + confirmación humana alcanza y es gratis.
