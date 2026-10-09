# TASK-011 — Verificación antes de publicar

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** orquestador (QA propia, no delegada)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama de integración
- **Depende de:** TASK-010
- **Estado:** `pending`

---

## Objetivo
Probar DD-4 (sin regresión con la config del usuario) y DD-2 (funciona sin config) antes de merge.

## Pasos
- [ ] **Paso 1** — repetir `antes-002/COMANDOS.txt` en `despues-002/` y diffear. Solo pueden
  cambiar token, fecha y el texto de mensajes que TASK-010 cambió a propósito.
- [ ] **Paso 2** — HOME vacío: `--help`, `need` y `plan` en un repo git temporal con un plan
  sintético; error claro fuera de un repo.
- [ ] **Paso 3** — `config.example.toml` copiado tal cual como config: carga sin error.
- [ ] **Paso 4** — mutaciones en el merge (dict vs lista, ausencia de `maquina_default`) en una copia
  scratch: cada una tiene que romper algún paso de arriba.
- [ ] **Paso 5** — `git grep` de TASK-010 vacío; merge `--no-ff` a `main`.

## Criterios de aceptación
- [ ] Diffs explicados línea por línea en el Resultado.
- [ ] Merge en `main` y `orq` instalado sigue funcionando para despachar (un `need` real).

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**
