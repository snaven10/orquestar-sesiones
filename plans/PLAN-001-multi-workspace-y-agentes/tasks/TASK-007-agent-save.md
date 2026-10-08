# TASK-007 — orq agent save --scope (scope obligatorio)

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-002
- **Estado:** `done`

---

## Objetivo
Guardar un agente aprobado en el scope que el usuario eligió — nunca un default (DD-5).

## Archivos
- **Modificar:** `assets/orq.py`

## Pasos
- [x] **Paso 1** — `orq agent save <draft> <arq>@<target> --scope p|m|g [--ws] [--force]`; sin `--scope` → rc=2 imprimiendo la tabla de scopes válidos del ws.
- [x] **Paso 2** — validar frontmatter: `name`, `description`, `model` ∈ sonnet|opus|haiku|fable.
- [x] **Paso 3** — `m` rechazado en ws `repo`; `p` crea `<repo>/.claude/agents/` si falta; no pisar sin `--force`.
- [x] **Paso 4** — escribir el `.md`, registrar en overlay, mover el draft a `~/.orq/drafts/guardados/`.
- [x] **Paso 5** — si el scope es `p` dentro de un repo git: avisar que `.claude/agents/<nombre>.md` queda sin commitear (no commitear solo).

## Criterios de aceptación
- [x] Sin `--scope` → rc=2. Con `--scope m` en claude-dashboard → rc=2.
- [x] Draft sin `model:` → rc≠0.
- [x] Tras `save --scope p`, `orq need` lo resuelve con origen `overlay` y `cmd_spawn` lo pasaría con `--agent`.

## Resultado
- **Estado final:** `done`
- **Resumen:** `orq agent save <draft> [<arq>@<target>] --scope p|m|g [--force]` (`cmd_agent_save`, `_git_raiz`, subparser `save` dentro de `ags`). Sin `--scope` rc=2 listando `texto_scopes` (el flag es `choices` sin default). Valida `name` (kebab-case), `description` y `model` ∈ sonnet|opus|haiku|fable. `m` rechazado en ws `repo` (y en `multi` sin `add_dir`); `p` en `multi` exige target concreto, crea `.claude/agents/` si falta; no pisa sin `--force`; avisa si otro agente homónimo de scope más cercano lo tapa. Registra el mapeo en el overlay (si se pasó destino), mueve draft y `.razones.md` a `~/.orq/drafts/guardados/` y, con scope `p` en repo git, avisa que queda sin commitear (no commitea).
- **Commit:** `8a43e43` (feat(orq): orq agent save con scope obligatorio)
- **Archivos tocados:** `assets/orq.py`
- **Verificado por:** `py_compile` OK. En claude-dashboard: sin `--scope` rc=2; `--scope m` rc=2; `--scope x` rc=2 (argparse); draft sin `model` rc=2; draft inexistente rc=2; `--ws mi-empresa` con `--scope p` sin target rc=2 y con target inexistente rc=2 (nada escrito); `--scope p` OK -> `.claude/agents/go-dashboard-worker.md` creado, overlay escrito, draft movido a `guardados/`; reintento sin `--force` rc=2, con `--force` OK; `--scope g` OK sin destino (avisa que no registró). Luego `orq need` resolvió `worker@claude-dashboard` con ORIGEN `overlay`. Limpieza: `.md` y `.claude/` borrados (no existía), `~/.claude/agents/` borrado (no existía). `cmd_spawn` pasaría `--agent go-dashboard-worker` por lectura de código (el gate/re-resolve es TASK-004). NO probado: `--scope m` real en mi-empresa (escribiría en `~/mi-empresa/.claude/agents`).
- **Desviaciones:** (1) `<arq>@<target>` es opcional: sin él se guarda pero no se registra (se imprime cómo hacerlo con `agent use`). (2) Se rechaza `scout` como arquetipo destino. (3) El orden de commits quedó `75b8bfb` scout -> `8a43e43` save -> docs de cierre de TASK-003, porque un `git add -A` del cierre de TASK-003 arrastró `orq.py` y hubo que rehacerlo con `reset --soft`.
- **Riesgos abiertos:** el scope `m` sólo valida `add_dir` declarado, no que el dir de agentes del monorepo exista (se crea). Para TASK-005: documentar que sin `<arq>@<target>` no hay overlay.
