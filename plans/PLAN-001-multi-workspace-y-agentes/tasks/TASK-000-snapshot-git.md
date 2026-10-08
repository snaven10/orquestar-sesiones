# TASK-000 — Snapshot de la skill antes de tocarla

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** directo (orquestador)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** — (primera del plan)
- **Estado:** `pending`

---

## Objetivo
Poder revertir cualquier cambio de este plan con git en vez de con `.bak` sueltos.

## Contexto verificado
- `~/.claude/skills` no es repo git. Hay un `roles.py.bak-20261008-093640` manual.
- `__pycache__/` dentro de `assets/`.

## Pasos
- [ ] `git init -b main` en `~/.claude/skills/orquestar-sesiones`, `.gitignore` con `__pycache__/` y `*.bak-*`.
- [ ] Commit base `chore: snapshot inicial de orquestar-sesiones` (sin atribución de AI).
- [ ] Capturar ANTES (sobre el commit base) en `~/.orq/regresion/antes/`: salida de `orq need` para 3 intents MI-EMPRESA representativos (backend, front, calidad) y `orq plan 133`. Sin `spawn`.

## Criterios de aceptación
- [ ] `git status` limpio y `git log` con 1 commit que incluye SKILL.md, assets/*.py, references/, plans/.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

