# TASK-001 — Workspaces declarativos (multi / repo)

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-000
- **Estado:** `done`

---

## Objetivo
orq trabaja en cualquier workspace declarado en `roles.py` (DD-1), sin cambiar la salida para `~/mi-empresa`.

## Contexto verificado
- `~/mi-empresa` fijo en roles.py:10, :22 (`maquinas.*.workspace`) y `add_dir_obligatorio` (roles.py:31).
- Usos en orq.py: 142 (`descubrir_targets`), 260, 365, 436 (`enlazar_agentes`), 458, 495, 638/640 (`--add-dir ws`), 819-820 (`PLANS`, `AGENTS_DIR`), `RUIDO` en 164.
- remota también tiene `~/mi-empresa`: `path` se resuelve contra el HOME remoto con `rpath` (orq.py:64), conservarlo.

## Archivos
- **Modificar:** `assets/roles.py`, `assets/orq.py`

## Pasos
- [x] **Paso 1** — agregar `workspaces` + `workspace_default` a roles.py (DD-1), con `mi-empresa` y `claude-dashboard`.
- [x] **Paso 2** — helper `resolver_ws(args, cfg)` (flag `--ws` global en el parser → cwd → default).
- [x] **Paso 3** — reemplazar cada uso de `maq(cfg)["workspace"]`, `PLANS`, `AGENTS_DIR`, `RUIDO`, `add_dir_obligatorio` por el ws resuelto.
- [x] **Paso 4** — `descubrir_targets`: tipo `repo` → `[basename(path)]` con el path absoluto como repo.
- [x] **Paso 5** — spawn: `--add-dir` solo si `ws.add_dir`; `enlazar_agentes` usa `ws_agents(ws)` y no hace nada si el ws es `repo` (el `.claude/agents` ya viaja en el repo).
- [x] **Paso 6** — `cmd_status`/`ls`/`reap`: mostrar columna `WS`; estado en `~/.orq/*.json` con clave prefijada por ws **solo para ws ≠ mi-empresa** (no migrar las claves existentes).

## Criterios de aceptación
- [x] `orq need "<intent MI-EMPRESA>"` y `orq plan 133` dan salida idéntica antes/después (diff de texto, excepto el token).
- [x] `orq --ws claude-dashboard need "implementar colector"` resuelve target `claude-dashboard` sin `--add-dir`.
- [x] `rg -n '"~/mi-empresa"|/ "mi-empresa"' assets/orq.py` → 0 resultados.

## Riesgos
Las claves `worker@<target>` de `sessions.json` podrían colisionar entre ws; por eso el prefijo para ws nuevos.

## Resultado
- **Estado final:** `done`
- **Resumen:** `roles.py` declara `workspaces` (`mi-empresa` multi, `claude-dashboard` repo) y `workspace_default`; se eliminaron `maquinas.*.workspace`, `add_dir_obligatorio` y `preflight.worktrees_en` (ahora por ws). `orq.py`: nuevas `resolver_ws` (`--ws` > `ORQ_WS` > cwd, gana el path más largo > default), `ws_actual`, `ws_ruta_target`, `clave_ws`, `ws_plans`, `ws_agents`; el flag global `--ws`; el token guarda `ws` y spawn lo respeta (no depende del cwd). `descubrir_targets` devuelve el propio repo en tipo `repo`; `--add-dir` solo si el ws lo declara; `enlazar_agentes` no hace nada en `repo`; `menciona` recibe el ruido del ws; claves de sesión con prefijo `<ws>:` solo fuera de mi-empresa; columna WS en `status`/`ls`/`reap`.
- **Commit:** `f11b31e` (feat(orq): workspaces declarativos multi/repo)
- **Archivos tocados:** `assets/orq.py`, `assets/roles.py`
- **Verificado por:** `py_compile` OK; regresión en `~/.orq/regresion/despues-001/` vs `antes/`: need-backend, need-front, need-calidad y plan-042 idénticos salvo el token aleatorio; `orq --ws claude-dashboard need "implementar colector"` (y sin `--ws` desde el cwd del repo) resuelve target `claude-dashboard`, token con `ws=claude-dashboard`; `rg -n '"~/mi-empresa"|/ "mi-empresa"' assets/orq.py` = 0 resultados. No se corrió spawn/scout.
- **Desviaciones:** (1) `spawn` real no se ejecutó (restricción), el no-`--add-dir` se verificó por lectura del código, no en vivo. (2) `worktrees_en` pasó a clave por ws (default `~/.orq/trees/<ws>` para `repo`) en vez de quedar en `preflight`. (3) Se agregó `ORQ_WS` como variable de entorno, no pedido. (4) La tabla de faltantes de `need` aún imprime los scopes con `~/mi-empresa` hardcodeado en texto (se reescribe en TASK-002/005). (5) El diseño dice que la skill "no es repo git"; sí lo es (rama main).
- **Riesgos abiertos:** el repo `claude-dashboard` aparece `dirty=1`/ACTIVO y rama `HEAD` (sin commits): para spawn el árbol exigirá definir rama. `ws_actual` se resuelve vía global `WS_NOMBRE`; TASK-002 debe usar `ws_agents(cfg)`/`ws_actual` y no rutas fijas.
