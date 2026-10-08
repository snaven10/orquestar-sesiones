# TASK-002 — Escalones 1-2: overlay, existencia y match por afinidad

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-001
- **Estado:** `done`

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
- [x] **Paso 1** — `cargar_overlay()`/`guardar_overlay()` sobre `~/.orq/specialists.json` (`{"<ws>": {"arq@target": "nombre"}}`).
- [x] **Paso 2** — `dirs_agentes(ws, target)` y `catalogo_agentes(ws, target)` → lista `{name, description, model, path, scope}`.
- [x] **Paso 3** — `señales_target(repo)` según `roles.py["señales"]` (DD-3).
- [x] **Paso 4** — `puntuar(agente, tags, arquetipo)` + bonus por mapeo previo en el mismo ws.
- [x] **Paso 5** — `resolver_specialist` → `{nombre|None, origen: overlay|roles|-, candidatos: [(nombre, score, tags)]}`; mapeado-pero-inexistente = faltante con aviso.
- [x] **Paso 6** — tabla de `need`/`plan`: columna ORIGEN; por faltante, top 3 candidatos o "sin candidatos → orq scout".
- [x] **Paso 7** — `orq agent use <nombre> <arq>@<target> [--ws]`: valida que el agente exista y lo escribe en el overlay.

## Criterios de aceptación
- [x] Con overlay vacío, la salida MI-EMPRESA solo difiere en la columna ORIGEN.
- [x] Para un target Quarkus sin mapeo (probar con un mapeo borrado temporalmente), `java-backend-specialist` sale primero en candidatos.
- [x] `worker@claude-dashboard` (repo Go sin `.claude/agents`) → faltante, sugiere `orq scout`.
- [x] Tras `agent use`, `need` lo resuelve con origen `overlay`.

## Resultado
- **Estado final:** `done`
- **Resumen:** `roles.py` suma `match_umbral` (0.5), `señales` (marcador de archivo -> tags, con `contiene` para distinguir Quarkus/Angular/Oracle), `tags_alias` y `arquetipo_señales`. `orq.py`: `cargar_overlay`/`guardar_overlay` (`~/.orq/specialists.json`), `parse_frontmatter` (a mano: comillas, `>`/`|`, escalares partidos, listas), `dirs_agentes`/`catalogo_agentes` (scopes p/m/g, el más cercano gana, `*.md.bak*` ignorados), `señales_target`, `puntuar`, `resolver_specialist` (ahora devuelve `{nombre, origen, candidatos, aviso}`; mapeado-pero-inexistente es faltante con aviso), `texto_scopes` (DD-5: en `repo` solo `[p]`/`[g]`), `lineas_candidatos`, `cmd_agent_use` y el subcomando `orq agent use`. `need` y `need --plan` muestran columna ORIGEN y, por faltante, top 3 con tags o `sin candidatos -> orq scout <arq>@<target>`; `plan` muestra ORIGEN (proyecto/monorepo/global) y candidatos para los nombres faltantes. La propuesta/token guarda `origen` y `candidatos`.
- **Commit:** `b5e6b2e` (feat(orq): resolución de specialists en escalones con match por afinidad)
- **Archivos tocados:** `assets/orq.py`, `assets/roles.py`
- **Verificado por:** `py_compile` OK. Regresión en `~/.orq/regresion/despues-002/` vs `antes/`: need-backend, need-front, need-calidad y plan-042 difieren solo en token y columna ORIGEN (en `need`: `roles`; en `plan`: `ORIGEN monorepo`). Match Quarkus (mapeos de BackEnd/FrontEnd/reviewer borrados en memoria con script): `api-backend` señales `[java, quarkus, oracle]` -> `java-backend-specialist 1.00 [java, quarkus, oracle]` primero (único sobre umbral); `web-frontend` -> `angular-frontend-architect 0.60 [nx, angular]`. `orq --ws claude-dashboard need "implementar colector"`: worker y reviewer faltantes, `sin candidatos -> orq scout worker@claude-dashboard`, scopes solo `[p]`/`[g]`. `agent use` (ok, agente inexistente rc=2, arquetipo inválido rc=2) y `need` posterior resuelve con ORIGEN `overlay`. `specialists.json` no existía antes: borrado; tokens de prueba borrados (36 como al inicio). No se corrió spawn/scout.
- **Desviaciones:** (1) El catálogo y las señales se leen del disco LOCAL (local), igual que `ws_agents`; con `--host remota` no se mira el disco remoto. (2) `roles.py["specialists"]` no está acotado por ws: en `claude-dashboard`, `reviewer@*` resuelve a `code-reviewer`, que no existe allí, y sale como faltante con aviso (aviso correcto, pero ruidoso; se puede acotar por ws en TASK-004/007). (3) El bonus de +0.1 usa los agentes mapeados en overlay del ws y en roles.py (no distingue por ws). (4) El score solo califica si hay al menos 1 tag acertado (un umbral 0.5 con un solo tag pasaría; los targets sin señales no proponen nada). (5) El frontmatter real de los agentes de MI-EMPRESA no usa `description: >` ni comillas ni `tools`; el parser los soporta igual pero está probado solo con strings sintéticos para esos casos. (6) `cmd_plan` marca `general-purpose` como faltante (es un agente built-in, no un .md): ya pasaba antes, no se tocó. (7) `agent use` valida el target contra `descubrir_targets` (acepta `*`).
- **Riesgos abiertos:** TASK-003/004: el dict de propuesta ahora lleva `origen` y `candidatos`; `specialist` sigue siendo `str|None`, así que el gate de spawn (`if p["specialist"]`, orq.py `cmd_spawn`) funciona sin cambios, pero debe re-resolver con `resolver_specialist(...)["nombre"]` (devuelve dict, ya no str). TASK-003: el scout debe reutilizar `señales_target` para el dossier y `catalogo_agentes` para no proponer algo que ya existe. TASK-007: `agent save` debe escribir en el overlay con `cargar_overlay`/`guardar_overlay` y usar `dirs_agentes` (scopes p/m/g) y `texto_scopes`. El subparser `agent` ya existe (`ags`): agregar `save` ahí, no crear otro.
