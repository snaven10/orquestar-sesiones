# TASK-001 — Workspaces declarativos (multi / repo)

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-000
- **Estado:** `pending`

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
- [ ] **Paso 1** — agregar `workspaces` + `workspace_default` a roles.py (DD-1), con `mi-empresa` y `claude-dashboard`.
- [ ] **Paso 2** — helper `resolver_ws(args, cfg)` (flag `--ws` global en el parser → cwd → default).
- [ ] **Paso 3** — reemplazar cada uso de `maq(cfg)["workspace"]`, `PLANS`, `AGENTS_DIR`, `RUIDO`, `add_dir_obligatorio` por el ws resuelto.
- [ ] **Paso 4** — `descubrir_targets`: tipo `repo` → `[basename(path)]` con el path absoluto como repo.
- [ ] **Paso 5** — spawn: `--add-dir` solo si `ws.add_dir`; `enlazar_agentes` usa `ws_agents(ws)` y no hace nada si el ws es `repo` (el `.claude/agents` ya viaja en el repo).
- [ ] **Paso 6** — `cmd_status`/`ls`/`reap`: mostrar columna `WS`; estado en `~/.orq/*.json` con clave prefijada por ws **solo para ws ≠ mi-empresa** (no migrar las claves existentes).

## Criterios de aceptación
- [ ] `orq need "<intent MI-EMPRESA>"` y `orq plan 133` dan salida idéntica antes/después (diff de texto, excepto el token).
- [ ] `orq --ws claude-dashboard need "implementar colector"` resuelve target `claude-dashboard` sin `--add-dir`.
- [ ] `rg -n '"~/mi-empresa"|/ "mi-empresa"' assets/orq.py` → 0 resultados.

## Riesgos
Las claves `worker@<target>` de `sessions.json` podrían colisionar entre ws; por eso el prefijo para ws nuevos.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

