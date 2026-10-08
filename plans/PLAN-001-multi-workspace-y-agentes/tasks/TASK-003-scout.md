# TASK-003 — Escalón 3: arquetipo scout + orq scout

- **Plan:** PLAN-001 — orq multi-workspace + agentes
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama `main`
- **Depende de:** TASK-002
- **Estado:** `done`

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
- [x] **Paso 1** — arquetipo `scout` en roles.py (DD-4). Excluirlo del loop `("worker","reviewer")` de `cmd_need`.
- [x] **Paso 2** — `need`: por cada faltante sin candidatos, agregar al token una entrada `scout` con costo estimado (~$0.15–0.30) y mostrarla en una sección "🔎 SCOUTS PROPUESTOS".
- [x] **Paso 3** — `orq scout --token T-… [--only N]`: valida token, arma dossier (señales, CLAUDE.md/AGENTS.md del repo, nombres en `~/.claude/projects/<slug>/memory/`, `git log --oneline -20`, tools/disallowed del arquetipo pedido), compone prompt (DD-4), corre en foreground con timeout 600 s, guarda `~/.orq/jobs/<jid>/out.json`.
- [x] **Paso 4** — extraer `<<<AGENTE … AGENTE>>>` y `<<<RAZONES … RAZONES>>>` del `result`; escribir `~/.orq/drafts/<nombre>.md` y `.razones.md`. Sin marcadores → rc=1 con ruta del out.json.
- [x] **Paso 5** — imprimir: ruta del draft, resumen de razones, scopes válidos del ws y el comando `orq agent save … --scope ?` **sin elegir scope**.
- [x] **Paso 6** — `orq scout` sin token → rc=2 (misma regla de oro que spawn).

## Criterios de aceptación
- [x] `orq scout` sin token o con token vencido → rc=2, ningún proceso `claude` lanzado.
- [x] Con un `claude` falso en PATH (script que imprime un JSON con marcadores) el draft se escribe bien; sin marcadores → rc=1.
- [x] El prompt generado nombra la skill del recommender y pide un ÚNICO agente con `model:` fijado.

## Riesgos
El JSON de `claude -p` podría no traer `result` si la sesión falla por permisos → leer también `is_error`/`subtype` y reportarlo.

## Resultado
- **Estado final:** `done`
- **Resumen:** `roles.py` suma el arquetipo `scout` (solo lectura, `maquina: local`, modelo sonnet, `costo` y `timeout` declarados). `orq.py`: `bin_claude(cfg, host)` (override `ORQ_CLAUDE`) y `flags_tools(a, quote)` (única construcción de `--allowedTools/--disallowedTools`, ahora usada por `cmd_spawn` y por el scout); `scouts_de`/`imprimir_scouts` (sección "SCOUTS PROPUESTOS" en `need` y `need --plan`: un scout por faltante SIN candidatos, el token guarda `scouts`); `repo_local`, `dossier_scout`, `prompt_scout`, `_extraer`, `cmd_scout` y el subcomando `orq scout [<arq>@<target>] --token T [--only N]`. El scout corre en foreground (timeout 600 s) con `claude -p --output-format json`, prompt por stdin desde `~/.orq/jobs/<jid>/prompt.txt`, salida en `out.json`; extrae `<<<AGENTE`/`<<<RAZONES` y escribe `~/.orq/drafts/<name>.md` y `.razones.md`. Imprime scopes válidos y `orq agent save <draft> <clave> --scope ?` sin elegir.
- **Commit:** `c3af96a` (feat(orq): escalón scout para proponer agentes faltantes)
- **Archivos tocados:** `assets/orq.py`, `assets/roles.py`
- **Verificado por:** `py_compile` OK. Con claude FALSO (`~/.orq/regresion/fake-bin/claude`, PATH primero + `ORQ_CLAUDE`, `which claude` confirmado antes de cada corrida; registra argv/stdin en `llamadas.log`): sin token, con `<arq>@<target>` sin token, token inexistente y token vencido -> rc=2 y 0 llamadas al falso; caso con marcadores -> draft + razones escritos (rc=0), reejecución con el mismo token -> rc=2 (ya costó); sin marcadores -> rc=1 con ruta de `out.json` y sin draft; JSON `is_error` -> rc=1 con subtype; draft sin `model` -> se escribe pero avisa. El argv del falso muestra los 11 `--allowedTools` y `--disallowedTools Write/Edit` sin shlex.quote; el stdin nombra la skill del recommender, la ruta de los templates, y pide UN agente con `model:` fijado. NO verificado en vivo: contra un `claude -p` real (formato real de `result`, permisos de las tools MCP en headless, que la skill se invoque de verdad).
- **Desviaciones:** (1) Gancho de prueba `ORQ_CLAUDE` en `bin_claude` (no estaba en el diseño): roles.py trae ruta absoluta, el PATH no alcanza. (2) El scout se marca `hecho` en el token ANTES de correr y no se puede repetir con ese token (cada corrida cuesta), a diferencia de spawn el token NO se consume (el mismo token sirve luego para spawn). (3) Un solo scout por invocación (`--only N`), no varios. (4) `lineas_candidatos` ya no imprime `orq scout <clave>` (sin token sería rc=2): dice "candidato a scout (ver SCOUTS PROPUESTOS)". (5) No se registra el job en `jobs.json` (no es una sesión de orquestación); sólo vive en `~/.orq/jobs/<jid>/`. (6) No se pasó `--add-dir`: el scout corre en el cwd del repo y el dossier ya lista los agentes existentes.
- **Riesgos abiertos:** el formato real de `result` y si `Skill`/MCPs corren en `-p` sin `--permission-mode` es lo primero que TASK-006 debe ver con el scout real. El dossier de memoria usa el slug `-home-...` de `~/.claude/projects` (verificado por convención, no contra un caso con memoria). Para TASK-005: el token de `need` ahora lleva `scouts`; el flujo es need -> scout -> save -> spawn con el mismo token.
