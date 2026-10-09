# TASK-009 — Loader de dos capas, ejemplo genérico y migración de la config del usuario

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), worktree de orq
- **Depende de:** TASK-008
- **Estado:** `done`

---

## Objetivo
`assets/roles.py` queda con defaults genéricos (sin nada de un usuario concreto) y orq aplica
encima `~/.orq/config.toml`. La config actual del usuario vive en ese archivo, fuera del repo, y
orq se comporta igual que antes (DD-1, DD-2, DD-3).

## Contexto verificado
- `load_cfg()` en `assets/orq.py` importa `roles.CFG` y le suma `_implicitos()`
  (`~/.orq/workspaces.json`).
- `HOST = os.environ.get("ORQ_HOST", "local")` (`orq.py:19`); `maq(cfg)` indexa `cfg["maquinas"][HOST]`.
- `ws_actual(cfg)` usa `WS_NOMBRE or cfg["workspace_default"]`.
- `_resolver_por_ruta` imprime "declaralo en roles.py" para workspaces implícitos.
- Claves del usuario hoy en `roles.py`: `maquinas`, `workspaces`, `workspace_default`,
  `specialists`, y en `recursos_exclusivos` todos menos `devctx_index`.
- Python 3.14 → `import tomllib`.

## Archivos
- **Crear:** `assets/config.example.toml`, `~/.orq/config.toml` (FUERA del repo)
- **Modificar:** `assets/orq.py` (`load_cfg`, `HOST`/`maq`, `ws_actual`, mensajes), `assets/roles.py`

## Pasos
- [ ] **Paso 1 — `~/.orq/config.toml`.** Volcar ahí, en TOML y conservando los comentarios que
  explican cada valor, `maquinas`, `maquina_default = "local"`, `workspaces`,
  `workspace_default`, `specialists` y los recursos exclusivos del usuario. Respaldo previo:
  `cp assets/roles.py ~/.orq/roles.py.antes-002`.
- [ ] **Paso 2 — `roles.py` genérico.** Quitar esas claves. Dejar: máquina `local`
  (`ssh: []`, `claude: "claude"`, concurrencia 2, `tiene_devctx: False`), `workspaces: {}`,
  `specialists: {}`, `recursos_exclusivos` solo con `devctx_index` (motivo genérico, sin nombres
  de archivos de esta máquina), y el resto tal cual.
- [ ] **Paso 3 — loader.** `load_cfg()`: carga `roles.CFG` (copia profunda), lee
  `ORQ_CONFIG` o `~/.orq/config.toml` si existe, merge profundo (dict pisa dict por clave; lista y
  escalar reemplazan), y después los implícitos. TOML inválido → error claro con la ruta y salida
  2, nunca un traceback.
- [ ] **Paso 4 — host y workspace.** `HOST` se resuelve tras cargar la config:
  `ORQ_HOST` → `cfg.get("maquina_default")` → `"local"`. Host inexistente → error que liste los
  declarados. Sin `workspace_default` y sin `--ws`/`ORQ_WS`: workspace implícito del repo del cwd
  (el mecanismo de `_resolver_por_ruta`); fuera de un repo → error claro.
- [ ] **Paso 5 — `config.example.toml`.** Comentado, con: una máquina local, una remota por SSH
  de ejemplo, un workspace `multi` (`~/proyectos/mi-empresa`, `add_dir`), uno `repo`, un
  specialist y un recurso exclusivo de ejemplo (`base_qa`). Nombres inventados, nada del usuario.
- [ ] **Paso 6 — mensajes.** Todo texto que diga "declaralo en roles.py" pasa a
  "declaralo en ~/.orq/config.toml".

## Criterios de aceptación
- [ ] `git grep -n -i -E 'mi-empresa|org|remota|_backend|-srv' assets/roles.py assets/config.example.toml` vacío.
- [ ] `python3 -m py_compile assets/orq.py assets/roles.py` OK.
- [ ] Con `~/.orq/config.toml`: las capturas de TASK-008 repetidas dan igual (eso lo cierra TASK-011,
  pero el worker lo corre antes de entregar y reporta el diff).
- [ ] `HOME=$(mktemp -d) python3 assets/orq.py --help` y `need` desde un repo git temporal funcionan
  sin config y sin traceback.
- [ ] `ORQ_CONFIG=` apuntando a un TOML roto → mensaje con la ruta, rc 2.

## Riesgos
- `tomllib` no distingue `None`: claves que hoy valen `None` (`add_dir`) se omiten en TOML y el
  código debe tratar ausencia = `None` (ya usa `setdefault`).
- Las claves de `roles.py` con `ñ` (`señales`, `arquetipo_señales`) son válidas en TOML solo
  entre comillas.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:** done
- **Resumen:** `roles.py` queda genérico (máquina `local`, `workspaces`/`specialists` vacíos, solo
  `devctx_index`; scout.maquina = `local`). La config del usuario vive en `~/.orq/config.toml`
  (incluye `[arquetipos.scout] maquina = "local"`); respaldo en `~/.orq/roles.py.antes-002`.
  `load_cfg()` hace deepcopy de `roles.CFG` + merge profundo del TOML (`ORQ_CONFIG` o
  `~/.orq/config.toml`) + implícitos; TOML roto / archivo ilegible / `ORQ_CONFIG` inexistente /
  host no declarado / sin ws → mensaje con ruta y rc 2. `HOST` = `--host` > `ORQ_HOST` >
  `maquina_default` > `local`, resuelto en `load_cfg`. `--host` ya no tiene `choices`. Sin
  `workspace_default` y fuera de un repo → error rc 2. Mensajes "declaralo en ~/.orq/config.toml".
  Etiqueta de origen `(roles)` en `need` se conserva. Extra: el binario `claude` pelado ("claude")
  se resuelve con `shutil.which` en scout. `assets/config.example.toml` creado.
- **Archivos tocados:** `assets/orq.py`, `assets/roles.py`, `assets/config.example.toml`,
  `~/.orq/config.toml` (fuera del repo)
- **Verificado por:** tomllib vs `roles.CFG` original igual (maquinas, workspaces,
  workspace_default, specialists, recursos); `py_compile`; regresión main vs worktree solo difiere
  en tokens, rutas de COMANDOS y texto de `--help`, más `⚠ ACTIVO` que es un auto-match de
  `pgrep -fa claude` con la ruta de `orq.py` (la de main contiene `.claude`); con una copia en una
  ruta con `claude` el diff desaparece; HOME vacío `--help`/`need` en repo temporal; ORQ_CONFIG
  roto/inexistente rc 2; `git grep` vacío.
