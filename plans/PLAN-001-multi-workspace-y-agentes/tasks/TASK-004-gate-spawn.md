# TASK-004 — Gate en spawn para sesiones sin specialist

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-002
- **Estado:** `done`

---

## Objetivo
`orq spawn` nunca más levanta una sesión genérica sin que el usuario lo haya aceptado (DD-6).

## Contexto verificado
- orq.py:641-642 `if p["specialist"]: flags += ["--agent", …]` — sin specialist no avisa.
- Spawn ya tiene gates rc=2 (token inválido, `--arbol`, `--destruccion`): seguir el mismo estilo.

## Archivos
- **Modificar:** `assets/orq.py`

## Pasos
- [x] **Paso 1** — antes de lanzar, recolectar `#N` sin specialist (re-resolver: el overlay pudo cambiar desde `need`).
- [x] **Paso 2** — rc=2 con mensaje DD-4 si alguno no está en `--sin-specialist`.
- [x] **Paso 3** — guardar la aceptación en el token y mostrarla en la línea de resultado de spawn (`general-purpose (aceptado)`).

## Criterios de aceptación
- [x] Token con sesión sin specialist + spawn sin flag → rc=2, nada lanzado (verificar `claude agents --json`).
- [x] Con `--sin-specialist N` → lanza y lo deja registrado.
- [x] Si entre `need` y `spawn` se guardó el agente, spawn lo usa sin pedir flag.

## Resultado
- **Estado final:** `done`
- **Resumen:** `cmd_spawn` llama a `gate_specialists` antes de cualquier otra validación o acción remota. `specialist_vigente(p, cfg)` re-resuelve: para filas de PLAN respeta el nombre declarado (basta que exista en el catálogo o sea built-in `general-purpose`, `AGENTES_BUILTIN`); para el resto usa `resolver_specialist(...)["nombre"]` y reemplaza `p["specialist"]`. Si falta alguno y no está en `--sin-specialist N[,M]` (numeración de filas de `need`, igual que `--only`): rc=2, nada lanzado, mensaje con aviso, candidatos, comando del scout si el token lo propone y las tres salidas (`agent use`, `scout`→`agent save`, `--sin-specialist`). La aceptación se guarda en `token["sin_specialist"]`, en `jobs.json` (`sin_specialist: true`) y se ve en la línea de resultado (`general-purpose (aceptado)`).
- **Commit:** `f469e3e` (feat(orq): spawn no levanta sesiones sin specialist en silencio)
- **Archivos tocados:** `assets/orq.py`
- **Verificado por:** con claude FALSO (PATH primero + `ORQ_CLAUDE`, `which claude` confirmado), en herramienta: spawn sin flag rc=2 (0 llamadas al falso, `jobs.json`/`sessions.json`/`worktrees.json` con md5 idéntico, 0 jobs nuevos); `--sin-specialist 7` rc=2; `--sin-specialist 1` (parcial) rc=2 listando solo #2; `--sin-specialist 1,2` lanza ambas, el argv del falso NO lleva `--agent`, jobs.json registra `sin_specialist: true`; tras `agent save --scope p` de `go-dashboard-worker`, `spawn --only 1` SIN flag lanza con `--agent go-dashboard-worker` (re-resolución entre need y spawn). Estado restaurado (tokens 36, jobs 36, json de `~/.orq` idénticos al backup). NO verificado: spawn en la máquina remota / `--visible` / worktrees con el gate (el gate corre antes y no toca esas ramas); la persistencia de `sin_specialist` en el token solo por lectura de código (el token se borra al terminar el spawn; sí queda en jobs.json).
- **Desviaciones:** (1) Cambio de comportamiento en `need --plan`: un specialist declarado por el PLAN que NO existe como .md (y no es `general-purpose`) ahora también bloquea; antes se lanzaba con `--agent` inexistente (sesión genérica silenciosa). (2) El gate lee el catálogo del disco LOCAL aun con `--host <maquina>` (mismo límite de TASK-002). (3) `jobs.json` suma el campo `sin_specialist`. (4) Para probar spawn con el falso se usó `ORQ_CLAUDE` (TASK-003).
- **Riesgos abiertos:** TASK-005 debe documentar `--sin-specialist` y que el gate re-resuelve (el flujo need → scout → save → spawn reutiliza el token). TASK-006: el spawn real de herramienta hereda `HEAD` sin commits (worker pide `--arbol`).
