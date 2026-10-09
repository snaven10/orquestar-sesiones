# TASK-008 — Capturas de regresión ANTES del cambio

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** general-purpose (haiku)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** — (primera del plan)
- **Estado:** `done`

---

## Objetivo
Dejar en `~/.orq/regresion/antes-002/` la salida de los comandos de solo lectura de orq con la
config actual, para comparar después de mover la config (DD-4).

## Contexto verificado
- Método previo: `~/.orq/regresion/antes/` (`need-backend.txt`, `need-calidad.txt`,
  `need-front.txt`, `plan-042.txt`), PLAN-001 TASK-000/TASK-006.
- `need` y `plan` NO levantan sesiones; `spawn` y `scout` sí → prohibidos en esta task.

## Pasos
- [ ] **Paso 1** — repetir los 4 comandos de `antes/` (ver su primera línea o PLAN-001 TASK-000)
  y guardarlos en `antes-002/` con el mismo nombre.
- [ ] **Paso 2** — sumar `orq --ws herramienta need "implementar PLAN-008"`,
  `orq --ws herramienta plan 8`, `orq status` y `orq --help` → `antes-002/`.
- [ ] **Paso 3** — anotar en `antes-002/COMANDOS.txt` el comando exacto de cada captura.

## Criterios de aceptación
- [ ] 8 archivos + `COMANDOS.txt` en `antes-002/`, ninguno vacío.
- [ ] Ningún `spawn`/`scout` ejecutado (`~/.orq/jobs.json` sin entradas nuevas).

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:** `done`
- **Resumen:** 8 capturas (`need` ×4 de mi-empresa y herramienta, `plan` de dos PLANes, `status`, `--help`) en `~/.orq/regresion/antes-002/`, todas rc=0, más `COMANDOS.txt`. Script reutilizable: `captura.sh <orq.py> <dir>`.
- **Archivos tocados:** `~/.orq/regresion/antes-002/*` (fuera del repo).
- **Verificado por:** orquestador; rc=0 y tamaño > 0 en las 8; sin `spawn`/`scout` (solo `need`, que emite tokens con TTL 10 min).
- **Desviaciones:** la salida de `need`/`status` depende del estado vivo de git y de las sesiones (ramas, dirty, ACTIVO). Por eso TASK-011 compara corriendo el `orq.py` de `main` y el del worktree **en el mismo momento**, y estas capturas quedan como registro.
