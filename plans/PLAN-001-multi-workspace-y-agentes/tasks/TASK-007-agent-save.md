# TASK-007 — orq agent save --scope (scope obligatorio)

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-002
- **Estado:** `pending`

---

## Objetivo
Guardar un agente aprobado en el scope que el usuario eligió — nunca un default (DD-5).

## Archivos
- **Modificar:** `assets/orq.py`

## Pasos
- [ ] **Paso 1** — `orq agent save <draft> <arq>@<target> --scope p|m|g [--ws] [--force]`; sin `--scope` → rc=2 imprimiendo la tabla de scopes válidos del ws.
- [ ] **Paso 2** — validar frontmatter: `name`, `description`, `model` ∈ sonnet|opus|haiku|fable.
- [ ] **Paso 3** — `m` rechazado en ws `repo`; `p` crea `<repo>/.claude/agents/` si falta; no pisar sin `--force`.
- [ ] **Paso 4** — escribir el `.md`, registrar en overlay, mover el draft a `~/.orq/drafts/guardados/`.
- [ ] **Paso 5** — si el scope es `p` dentro de un repo git: avisar que `.claude/agents/<nombre>.md` queda sin commitear (no commitear solo).

## Criterios de aceptación
- [ ] Sin `--scope` → rc=2. Con `--scope m` en claude-dashboard → rc=2.
- [ ] Draft sin `model:` → rc≠0.
- [ ] Tras `save --scope p`, `orq need` lo resuelve con origen `overlay` y `cmd_spawn` lo pasaría con `--agent`.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

