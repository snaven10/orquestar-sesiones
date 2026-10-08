# TASK-005 — Actualizar SKILL.md y escenarios.md

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-003, TASK-004, TASK-007
- **Estado:** `pending`

---

## Objetivo
El contrato de la skill describe el flujo real: workspaces, `--ws`, `agent draft/save`, gate de spawn.

## Archivos
- **Modificar:** `SKILL.md`, `references/escenarios.md`

## Pasos
- [ ] **Paso 1** — SKILL.md §1: `--ws` y cómo se elige el workspace.
- [ ] **Paso 2** — SKILL.md §3 reescrito como pasos: `3 escalones: confirmado → candidatos (`agent use`) → `scout` con token (aval) → presentar draft + razones + scopes válidos → **PARAR y preguntar scope** → `agent save --scope`.
- [ ] **Paso 3** — §4: documentar `--sin-specialist`. Trampas: "nombre en roles.py sin archivo = faltante".
- [ ] **Paso 4** — escenarios.md: escenario 17 "specialist faltante / workspace ajeno a MI-EMPRESA" con mitigación.
- [ ] **Paso 5** — quitar supuestos MI-EMPRESA del texto genérico (dejar los MI-EMPRESA como ejemplos marcados).

## Criterios de aceptación
- [ ] Cada comando citado en SKILL.md existe en `orq --help`.
- [ ] La regla de oro y el "PARÁ" tras presentar siguen explícitos.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

