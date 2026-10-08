# TASK-003 — Escalón 3: arquetipo scout + orq scout

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-002
- **Estado:** `pending`

---

## Objetivo
Cuando no hay agente que sirva, `orq` lanza (con aval) una sesión investigadora que usa `claude-automation-recommender` + devctx + context7 y deja un borrador de agente en `~/.orq/drafts/` (DD-4).

## Contexto verificado
- Spawn headless ya existe: `claude -p --output-format json`, prompt por stdin, `--allowedTools` por tool (orq.py:~636-648). Reutilizar esa construcción de flags, no duplicarla.
- Skill: `claude-code-setup:claude-automation-recommender` (read-only, `references/subagent-templates.md` en `~/.claude/plugins/cache/claude-plugins-official/claude-code-setup/1.0.0/skills/claude-automation-recommender/`).
- remota no tiene devctx → el scout corre siempre en local.
- Tokens: `need` emite `T-xxxxxx` en `~/.orq/tokens/` con `propuesta`; TTL `TOKEN_TTL`.

## Archivos
- **Modificar:** `assets/roles.py` (arquetipo `scout`), `assets/orq.py`

## Pasos
- [ ] **Paso 1** — arquetipo `scout` en roles.py (DD-4). Excluirlo del loop `("worker","reviewer")` de `cmd_need`.
- [ ] **Paso 2** — `need`: por cada faltante sin candidatos, agregar al token una entrada `scout` con costo estimado (~$0.15–0.30) y mostrarla en una sección "🔎 SCOUTS PROPUESTOS".
- [ ] **Paso 3** — `orq scout --token T-… [--only N]`: valida token, arma dossier (señales, CLAUDE.md/AGENTS.md del repo, nombres en `~/.claude/projects/<slug>/memory/`, `git log --oneline -20`, tools/disallowed del arquetipo pedido), compone prompt (DD-4), corre en foreground con timeout 600 s, guarda `~/.orq/jobs/<jid>/out.json`.
- [ ] **Paso 4** — extraer `<<<AGENTE … AGENTE>>>` y `<<<RAZONES … RAZONES>>>` del `result`; escribir `~/.orq/drafts/<nombre>.md` y `.razones.md`. Sin marcadores → rc=1 con ruta del out.json.
- [ ] **Paso 5** — imprimir: ruta del draft, resumen de razones, scopes válidos del ws y el comando `orq agent save … --scope ?` **sin elegir scope**.
- [ ] **Paso 6** — `orq scout` sin token → rc=2 (misma regla de oro que spawn).

## Criterios de aceptación
- [ ] `orq scout` sin token o con token vencido → rc=2, ningún proceso `claude` lanzado.
- [ ] Con un `claude` falso en PATH (script que imprime un JSON con marcadores) el draft se escribe bien; sin marcadores → rc=1.
- [ ] El prompt generado nombra la skill del recommender y pide un ÚNICO agente con `model:` fijado.

## Riesgos
El JSON de `claude -p` podría no traer `result` si la sesión falla por permisos → leer también `is_error`/`subtype` y reportarlo.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**

