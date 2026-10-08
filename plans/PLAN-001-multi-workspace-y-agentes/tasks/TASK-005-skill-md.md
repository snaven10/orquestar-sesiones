# TASK-005 — Actualizar SKILL.md y escenarios.md

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-003, TASK-004, TASK-007
- **Estado:** `done`

---

## Objetivo
El contrato de la skill describe el flujo real: workspaces, `--ws`, `agent draft/save`, gate de spawn.

## Archivos
- **Modificar:** `SKILL.md`, `references/escenarios.md`

## Pasos
- [x] **Paso 1** — SKILL.md §1: `--ws` y cómo se elige el workspace.
- [x] **Paso 2** — SKILL.md §3 reescrito como pasos: `3 escalones: confirmado → candidatos (`agent use`) → `scout` con token (aval) → presentar draft + razones + scopes válidos → **PARAR y preguntar scope** → `agent save --scope`.
- [x] **Paso 3** — §4: documentar `--sin-specialist`. Trampas: "nombre en roles.py sin archivo = faltante".
- [x] **Paso 4** — escenarios.md: escenario 17 "specialist faltante / workspace ajeno a MI-EMPRESA" con mitigación.
- [x] **Paso 5** — quitar supuestos MI-EMPRESA del texto genérico (dejar los MI-EMPRESA como ejemplos marcados).

## Criterios de aceptación
- [x] Cada comando citado en SKILL.md existe en `orq --help`.
- [x] La regla de oro y el "PARÁ" tras presentar siguen explícitos.

## Resultado
- **Estado final:** `done`
- **Resumen:** SKILL.md §1 documenta workspaces (`multi`/`repo`), `--ws` > `ORQ_WS` > cwd > default y que `--add-dir` solo va si el ws lo declara. §3 reescrito en 3 escalones con comandos exactos (`agent use`, `scout --token`, `agent save --scope`), con los PARÁ (candidatos, aval del scout, scope) y tabla de scopes por tipo de ws; las fuentes (devctx, memoria, context7, recommender) pasan a ser del scout. §4 documenta el gate y `--sin-specialist`. Trampas: add_dir condicionado al ws, nombre mapeado sin `.md` = faltante, catálogo del disco local con `--host remota`, `ORQ_CLAUDE` solo tests. Escenario 17 agregado. Regla de oro y "Nunca" intactos.
- **Commit:** `aa490fb` (docs(skill): contrato de 3 escalones, workspaces y gate de specialists)
- **Archivos tocados:** `SKILL.md`, `references/escenarios.md`
- **Verificado por:** `orq --help`, `agent --help`, `agent use --help`, `agent save --help`, `scout --help`, `spawn --help`, `need --help`: todos los comandos y flags citados existen. No se corrió spawn/scout/need.
- **Desviaciones:** (1) El plan menciona `agent draft`: NO existe; el draft lo escribe `orq scout`. (2) El plan dice que el scout corre "como spawn"; en código el token no se consume y el scout no se repite con ese token. (3) `<arq>@<target>` es opcional en `save` (sin él no hay overlay). (4) `need --plan` bloquea por specialist declarado inexistente. (5) `need` aún imprime scopes con `~/mi-empresa` hardcodeado según TASK-001 (no re-verificado; código no tocado). (6) Escenario 17 se apoya en la desviación 2 de TASK-002 (`reviewer@*` -> `code-reviewer` ausente en claude-dashboard).
