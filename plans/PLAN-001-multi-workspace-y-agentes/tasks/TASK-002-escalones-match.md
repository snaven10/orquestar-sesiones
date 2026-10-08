# TASK-002 — Escalones 1-2: overlay, existencia y match por afinidad

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-001
- **Estado:** `pending`

---

## Objetivo
`resolver_specialist` implementa los escalones 1 y 2 de DD-2/DD-3: usa lo confirmado, y si no hay, propone candidatos del disco con puntaje.

## Contexto verificado
- `resolver_specialist` orq.py:190 hoy solo mira `cfg["specialists"]`.
- `need_de_plan`/`cmd_plan` comparan contra `AGENTS_DIR` con glob (orq.py:364, :1029).
- `~/mi-empresa/.claude/agents/` tiene ~18 agentes con frontmatter (`name`, `description`, `model`, `tools`). `~/.claude/agents/` no existe hoy.
- Python sin pip ni yaml → parser de frontmatter a mano (líneas `clave: valor` entre `---`; `description` puede ser multilínea con `>`).

## Archivos
- **Modificar:** `assets/orq.py`, `assets/roles.py` (tabla `señales`, `match_umbral`)

## Pasos
- [ ] **Paso 1** — `cargar_overlay()`/`guardar_overlay()` sobre `~/.orq/specialists.json` (`{"<ws>": {"arq@target": "nombre"}}`).
- [ ] **Paso 2** — `dirs_agentes(ws, target)` y `catalogo_agentes(ws, target)` → lista `{name, description, model, path, scope}`.
- [ ] **Paso 3** — `señales_target(repo)` según `roles.py["señales"]` (DD-3).
- [ ] **Paso 4** — `puntuar(agente, tags, arquetipo)` + bonus por mapeo previo en el mismo ws.
- [ ] **Paso 5** — `resolver_specialist` → `{nombre|None, origen: overlay|roles|-, candidatos: [(nombre, score, tags)]}`; mapeado-pero-inexistente = faltante con aviso.
- [ ] **Paso 6** — tabla de `need`/`plan`: columna ORIGEN; por faltante, top 3 candidatos o "sin candidatos → orq scout".
- [ ] **Paso 7** — `orq agent use <nombre> <arq>@<target> [--ws]`: valida que el agente exista y lo escribe en el overlay.

## Criterios de aceptación
- [ ] Con overlay vacío, la salida MI-EMPRESA solo difiere en la columna ORIGEN.
- [ ] Para un target Quarkus sin mapeo (probar con un mapeo borrado temporalmente), `java-backend-specialist` sale primero en candidatos.
- [ ] `worker@claude-dashboard` (repo Go sin `.claude/agents`) → faltante, sugiere `orq scout`.
- [ ] Tras `agent use`, `need` lo resuelve con origen `overlay`.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

