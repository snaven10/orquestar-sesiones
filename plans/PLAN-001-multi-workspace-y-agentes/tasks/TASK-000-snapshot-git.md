# TASK-000 — Snapshot de la skill antes de tocarla

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** directo (orquestador)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** — (primera del plan)
- **Estado:** `done`

---

## Objetivo
Poder revertir cualquier cambio de este plan con git en vez de con `.bak` sueltos.

## Contexto verificado
- `~/.claude/skills` no es repo git. Hay un `roles.py.bak-20261008-093640` manual.
- `__pycache__/` dentro de `assets/`.

## Pasos
- [x] `git init -b main` en `~/.claude/skills/orquestar-sesiones`, `.gitignore` con `__pycache__/` y `*.bak-*`.
- [x] Commit base `chore: snapshot inicial de orquestar-sesiones` (sin atribución de AI).
- [x] Capturar ANTES (sobre el commit base) en `~/.orq/regresion/antes/`: salida de `orq need` para 3 intents mi-empresa representativos (backend, front, calidad) y `orq plan 042`. Sin `spawn`.

## Criterios de aceptación
- [x] `git status` limpio y `git log` con 1 commit que incluye SKILL.md, assets/*.py, references/, plans/.

## Resultado
- **Estado final:** `done`
- **Resumen:** repo git local en la skill con commit base `a621d0d`; identidad git local copiada de api-backend. Capturas "antes" en `~/.orq/regresion/antes/` (need backend/front/calidad + plan 042, todos rc=0).
- **Archivos tocados:** `.gitignore` (nuevo), `.git/`.
- **Verificado por:** `git log` = 1 commit; 4 capturas de 20-25 líneas.
- **Riesgos abiertos / siguiente:** las capturas dependen del estado vivo de los repos (rama, dirty, ACTIVO, `resume <sid>`) y del token: el diff de TASK-006 tiene que ignorar esas líneas o recapturar ambas al mismo tiempo.
