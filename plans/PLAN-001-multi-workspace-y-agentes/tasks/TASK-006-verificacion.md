# TASK-006 — Verificación: no-regresión mi-empresa + dry-run en herramienta

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-005
- **Estado:** `pending`

---

## Objetivo
Probar end-to-end sin gastar sesiones: todo con `need`/`plan`/`agent draft`, **ningún `spawn` real**.

## Pasos
- [ ] **Paso 1** — repetir las capturas de TASK-000 en `~/.orq/regresion/despues/` y diffear.
- [ ] **Paso 2** — `orq --ws herramienta need "implementar PLAN-001"` y `orq --ws herramienta plan 1`.
- [ ] **Paso 3** — `orq scout` real para `worker@herramienta` — **pedir aval al usuario antes** (cuesta). Revisar el draft; NO guardarlo: el scope lo elige el usuario.
- [ ] **Paso 4** — `spawn` con token de herramienta sin specialist → debe dar rc=2.
- [ ] **Paso 5** — `python3 -m py_compile assets/orq.py assets/roles.py`.

## Criterios de aceptación
- [ ] Diffs mi-empresa vacíos (salvo token y columna de origen).
- [ ] Los 4 pasos de herramienta se comportan como dicen DD-1..DD-5; cualquier desvío se reporta, no se parchea en esta task.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

