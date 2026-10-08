# TASK-004 — Gate en spawn para sesiones sin specialist

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-002
- **Estado:** `pending`

---

## Objetivo
`orq spawn` nunca más levanta una sesión genérica sin que el usuario lo haya aceptado (DD-6).

## Contexto verificado
- orq.py:641-642 `if p["specialist"]: flags += ["--agent", …]` — sin specialist no avisa.
- Spawn ya tiene gates rc=2 (token inválido, `--arbol`, `--destruccion`): seguir el mismo estilo.

## Archivos
- **Modificar:** `assets/orq.py`

## Pasos
- [ ] **Paso 1** — antes de lanzar, recolectar `#N` sin specialist (re-resolver: el overlay pudo cambiar desde `need`).
- [ ] **Paso 2** — rc=2 con mensaje DD-4 si alguno no está en `--sin-specialist`.
- [ ] **Paso 3** — guardar la aceptación en el token y mostrarla en la línea de resultado de spawn (`general-purpose (aceptado)`).

## Criterios de aceptación
- [ ] Token con sesión sin specialist + spawn sin flag → rc=2, nada lanzado (verificar `claude agents --json`).
- [ ] Con `--sin-specialist N` → lanza y lo deja registrado.
- [ ] Si entre `need` y `spawn` se guardó el agente, spawn lo usa sin pedir flag.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

