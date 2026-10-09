# PLAN-002 — Config del usuario fuera del código + publicación en GitHub

**Fecha:** 2026-10-09
**Fase:** 2 (Ejecución) — aprobado 2026-10-09
**Fase anterior:** [PLAN-001](../PLAN-001-multi-workspace-y-agentes/PLAN-001-multi-workspace-y-agentes.md)
**Proyectos:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`)
**Origen:** pedido del usuario — publicar orq como repo público (MIT) para aportes de la comunidad

## 1. Qué resuelve
`assets/roles.py` mezcla dos cosas: la **política genérica** de orq (arquetipos, señales de stack,
política de árbol, normalización de estados) y la **config de un usuario concreto** (sus máquinas,
sus workspaces, sus specialists, los recursos exclusivos de su cliente). Con eso adentro orq no se
puede publicar ni le sirve a otro: el default es un workspace que solo existe en esta máquina.
Este plan separa la config del usuario a `~/.orq/config.toml` (nunca entra al repo), deja un
ejemplo genérico, y después reescribe el historial y publica.

## 2. Hallazgos (verificados 2026-10-09)
- **Ya existe la mitad del mecanismo.** `load_cfg()` (`assets/orq.py`) importa `roles.CFG` y le
  aplica encima `~/.orq/workspaces.json` (implícitos); `cargar_overlay()` lee
  `~/.orq/specialists.json`. Falta un archivo de config del usuario que pise el resto.
- **Qué es del usuario en `roles.py`:** `maquinas` (local y remotas, ssh, concurrencia), `workspaces` +
  `workspace_default`, `specialists`, y 5 de los 6 `recursos_exclusivos` (todos con
  `solo_ws` de un solo workspace). Lo demás es genérico.
- **`HOST` estaba fijado al nombre de una máquina del autor** (`orq.py:19`, `ORQ_HOST` o ese nombre): otro usuario no tiene esa máquina.
- **Menciones al cliente en el árbol y el historial.** Hay nombres del cliente del usuario
  (repos, planes, máquinas, una IP privada y rutas del HOME) repartidos en código, `SKILL.md`,
  `references/` y los planes, y en el historial git. No se listan acá: la lista privada vive
  fuera del repo y alimenta el grep de verificación.
- **Python 3.14** local → `tomllib` en la stdlib: TOML se lee sin pip y **admite comentarios**
  (los de `roles.py` explican el porqué de cada valor; JSON los perdería).
- **Regresión ya montada:** `~/.orq/regresion/antes/` tiene capturas de `need`/`plan` de PLAN-001
  (TASK-000/006). Se reusa el método.
- **`git-filter-repo` no está instalado** y no hay `brew`/`pip`. Es un único script Python: se baja
  la release fijada al scratchpad.
- **Los SHAs citados en los planes van a quedar viejos** tras reescribir (cambian todos los
  hashes). `filter-repo` reescribe los SHAs dentro de los mensajes de commit, no dentro de archivos.

## 3. Decisiones de diseño
- **DD-1 — Dos capas.** `assets/roles.py` queda solo con defaults genéricos. Encima se aplica
  `~/.orq/config.toml` (o la ruta de `ORQ_CONFIG`, para tests). Merge profundo de dicts: una clave
  del usuario pisa la del default; las listas se reemplazan, no se concatenan.
- **DD-2 — Sin config, orq funciona.** Default de máquina: `local` (`ssh: []`, `claude` = el del
  PATH, concurrencia 2). Sin `workspace_default`: el workspace sale del repo del cwd (implícito,
  mecanismo que ya existe) o error claro si no estás en un repo. `HOST` = `ORQ_HOST` →
  `maquina_default` de la config → `local`.
- **DD-3 — TOML para lo que escribe el humano, JSON para lo que escribe orq.** `config.toml` es de
  solo lectura para orq (`tomllib` no escribe). `specialists.json`, `workspaces.json`, `jobs.json`
  siguen igual.
- **DD-4 — Regla dura de no regresión.** Con la config del usuario migrada, `need` y `plan` dan la
  MISMA salida que hoy (salvo token y fecha). Si no, no se sigue a publicar.
- **DD-5 — Publicar = historial reescrito, no repo nuevo.** `filter-repo --replace-text` +
  `--replace-message` en un clone aparte, con respaldo `--mirror`. Verificación sobre
  `git log --all -p` completo. Nota en el README: los SHAs citados en `plans/` son de antes de la
  publicación.

## 4. Tasks y orden
| Task | Qué | Especialista | Modelo | Depende de | Estado |
|------|-----|--------------|--------|------------|--------|
| **TASK-008** | Capturas de regresión ANTES (need/plan con la config actual) | general-purpose | haiku | — | `done` |
| **TASK-009** | Loader de dos capas + `config.example.toml` + migrar la config del usuario a `~/.orq/config.toml` | general-purpose | sonnet | TASK-008 | `pending` |
| **TASK-010** | Texto genérico en `orq.py`, `SKILL.md`, `references/`, planes; `README.md` + `LICENSE` MIT | general-purpose | sonnet | TASK-009 | `pending` |
| **TASK-011** | Verificación: regresión idéntica + HOME vacío funciona + árbol sin menciones | orquestador | — | TASK-010 | `pending` |
| **TASK-012** | Reescribir historial y publicar (gate del usuario antes del push) | orquestador | — | TASK-011 + PLAN-009 del dashboard | `pending` |

Todo secuencial: cada task pisa los mismos archivos que la anterior.

## 5. Fuera de alcance
- Cambiar comportamiento de orq (resolución de specialists, spawn, reap). Esto es mover config,
  no rediseñar.
- Empaquetar orq (pip, brew). Se instala clonando en `~/.claude/skills/`.
- Traducir al inglés. Se publica en español; un README en inglés puede venir después.
- Migrar `~/.orq/*.json` existentes: su formato no cambia.

## 6. Cierre
<!-- SE LLENA AL CERRAR EL PLAN -->
