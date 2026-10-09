<div align="center">

# 🎼 orquestar-sesiones (`orq`)

**Un director de orquesta para tus sesiones de Claude Code.**

Vos decís *qué* hay que hacer. `orq` propone *quién* lo hace, *dónde*, *cuánto cuesta arrancar* —
y **no levanta nada hasta que digas que sí**.

![Python](https://img.shields.io/badge/Python-%E2%89%A5%203.11-3776AB?logo=python&logoColor=white)
![Deps](https://img.shields.io/badge/dependencias-0-success)
![Skill](https://img.shields.io/badge/Claude%20Code-skill-D97757)
![License](https://img.shields.io/badge/licencia-MIT-blue)

</div>

---

## La idea

Paralelizar con Claude Code es fácil. Paralelizar **bien** no:

- Levantás 5 sesiones y 2 eran innecesarias: cada arranque cuesta 20–40k tokens de preámbulo.
- Un worker cae en `general-purpose` **en silencio** porque no encontró su agente, y te entrega
  trabajo sin criterio de dominio.
- Dos worktrees "aislados" corren la misma migración contra la misma base y se pisan.
- Revisás cambios sin commitear en un worktree nuevo… que no los tiene.

`orq` es una **skill de Claude Code** más un script de un solo archivo (`assets/orq.py`, solo
stdlib) que convierte todo eso en un flujo con frenos:

```
  need  ──►  propuesta + costo + token  ──►  vos aprobás  ──►  spawn  ──►  status  ──►  harvest
            (qué sesiones, qué agente,                         (worktree                (lo que
             qué árbol, qué falta)                              por tarea)               aprendieron)
```

## Qué hace

**🧾 Propone antes de gastar.** `orq need "lo que querés hacer"` detecta los repos involucrados,
arma la tabla de sesiones (arquetipo, target, agente, árbol de git), estima el costo de arranque y
emite un **token de 10 minutos**. `spawn` sin token sale con `rc=2`. No hay flag para saltárselo.

**📋 Despacha planes por olas.** `orq need --plan 7 --lote 2` lee un plan en markdown
(`plans/PLAN-007-*/`), toma las tareas del lote, respeta el specialist que pide cada una y levanta un
worktree por tarea.

**🧠 Encuentra el agente correcto — o te dice que falta.** Resolución en tres escalones:
1. **Confirmado:** está en tu config o lo aprobaste antes.
2. **Match:** puntúa los agentes del disco contra el stack del repo (`go.mod` → go,
   `pom.xml` con quarkus → java + quarkus…). Solo **propone**; vos confirmás con `orq agent use`.
3. **Scout:** una sesión barata de solo lectura investiga el repo y redacta un agente nuevo. Lo
   guardás con `orq agent save`, eligiendo el scope (proyecto o global) — nunca hay default.

**🌳 Decide el árbol con reglas, no con suerte.** Auditar algo commiteado → worktree fijo al SHA.
Auditar algo sin commitear → el árbol original, obligatorio (un worktree nuevo no ve tus cambios).
Implementar en paralelo → un worktree y una rama por tarea. Cada worktree nace con su política de
destrucción (`nunca`, `si_limpio`, `tras_merge`) y `orq reap` la aplica.

**🔒 Locks por recurso, no por repo.** Declarás recursos exclusivos (una base de QA, una cola de
ETL, el índice de búsqueda) con las palabras que los delatan. Si dos tareas los tocan, no corren
juntas, aunque vivan en repos distintos.

**🖥️ Local o remoto.** Declarás máquinas en la config; con `--host` las sesiones corren por SSH en
otra máquina, con su propia concurrencia.

**🌾 Cosecha.** `orq harvest` recoge el resultado de cada sesión y lo que aprendió, para que la
próxima no tropiece con lo mismo.

## Instalación

Requisitos: **[Claude Code](https://claude.com/claude-code)** con sesión iniciada, **Python ≥ 3.11**
y **git**.

```bash
git clone https://github.com/snaven10/orquestar-sesiones.git ~/.claude/skills/orquestar-sesiones

# el comando `orq` (~/.local/bin tiene que estar en el PATH)
mkdir -p ~/.local/bin
cat > ~/.local/bin/orq <<'WRAP'
#!/bin/sh
exec python3 "$HOME/.claude/skills/orquestar-sesiones/assets/orq.py" "$@"
WRAP
chmod +x ~/.local/bin/orq
```

Al estar en `~/.claude/skills/`, Claude Code carga la skill sola: pedile *"levantá sesiones para
esto en paralelo"* y va a seguir el contrato de [`SKILL.md`](SKILL.md).

## Configuración

**Sin config, funciona**: corre en tu máquina (`local`) y usa como workspace el repo git en el que
estás parado. Cuando quieras más, copiá el ejemplo:

```bash
mkdir -p ~/.orq
cp ~/.claude/skills/orquestar-sesiones/assets/config.example.toml ~/.orq/config.toml
```

```toml
maquina_default = "local"

[maquinas.servidor]                      # otra máquina, por SSH
ssh = ["ssh", "-o", "BatchMode=yes", "servidor"]
claude = "~/.local/bin/claude"
concurrencia = 4

[workspaces.mi-empresa]                  # un directorio con varios repos adentro
path = "~/proyectos/mi-empresa"
tipo = "multi"
add_dir = "~/proyectos/mi-empresa"       # para que encuentre los agentes del workspace

[specialists]
"worker@api-backend" = "java-backend-specialist"

[recursos_exclusivos.base_qa]
motivo = "una sola base de QA: dos migraciones a la vez se pisan"
detectar = ["migración", "ddl", "seed"]
```

Tu `config.toml` es **tuyo**: vive fuera del repo y se aplica encima de los defaults genéricos de
[`assets/roles.py`](assets/roles.py). Cada campo está comentado en
[`assets/config.example.toml`](assets/config.example.toml).

## Primer uso

```bash
cd ~/proyectos/mi-repo
orq need "agregar paginación al endpoint de órdenes y revisar el diff"
#   → tabla con worker + reviewer, agentes, árbol, costo estimado y token T-3fa91c
orq spawn --token T-3fa91c --arbol worktree --destruccion tras_merge
orq status            # qué está corriendo, dónde, y el comando para engancharte
orq reap --force      # limpia los worktrees que ya cumplieron su política
```

## Trampas que ya pisamos (para que vos no)

Todo esto está verificado en uso real y documentado en [`SKILL.md`](SKILL.md):

- En un workspace `multi`, sin `--add-dir` el agente **no resuelve y cae a `general-purpose` en
  silencio**. `orq` pasa el flag si el workspace lo declara.
- `attach` a una sesión terminada **la revive**, y al salir abre una sesión nueva en `~`. Para leer
  una sesión terminada: `claude logs <id>`.
- `Estado: done` en un markdown no prueba nada: en un corpus real, 3 de 131 `done` tenían evidencia.
  `orq` verifica contra git.
- `pkill -f` es una ruleta: la skill prohíbe matar por patrón; las sesiones se paran por id (`claude stop <id>`).

## Cómo se construyó

Con Claude Code, plan por plan: el diseño y la verificación de cada cambio están en
[`plans/`](plans/).

> Los SHAs citados en `plans/` son de antes de publicar el repo (el historial se reescribió para
> quitar datos privados) y ya no existen acá.

¿Usás muchas sesiones? Combinalo con
**[claude-dashboard](https://github.com/snaven10/claude-dashboard)**, que muestra los workers de
`orq` con su plan y su tarea.

## Contribuir

Issues y PRs bienvenidos. Antes de mandar un cambio: `python3 -m py_compile assets/orq.py`, y probá
`orq need` / `orq plan` con `HOME` vacío (sin config) y con el ejemplo
(`ORQ_CONFIG=assets/config.example.toml`). **Nunca** pruebes `spawn` sin entender que levanta
sesiones reales: para eso existe `ORQ_CLAUDE`, que lo reemplaza por un binario falso.

## Licencia

[MIT](LICENSE) © 2026 snaven10
