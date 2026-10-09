# TASK-010 — Texto genérico, README y LICENSE MIT

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), worktree de orq
- **Depende de:** TASK-009
- **Estado:** `done`

---

## Objetivo
Ningún archivo versionado nombra al cliente, sus repos, sus planes ni las máquinas del usuario.
Los ejemplos pasan a nombres inventados y el repo trae README de instalación y licencia.

## Contexto verificado
- Menciones actuales: `assets/orq.py` (10, comentarios/docstrings, p. ej. el docstring con
  `api-backend (`/ruta/`)`), `SKILL.md` (9, incluye `--add-dir ~/proyectos/mi-empresa` y referencias a
  `roles.py["workspaces"]`), `references/escenarios.md` (6), `plans/PLAN-001-*` (~40).
- Otros identificadores en el árbol: nombres de máquinas del usuario, su HOME y una IP privada de VPN.

## Pasos
- [x] **Paso 1 — código.** Comentarios y docstrings de `orq.py` con ejemplos genéricos
  (`mi-empresa`, `api-backend`, `web-frontend`). El comportamiento no cambia: solo texto.
- [x] **Paso 2 — `SKILL.md` y `references/`.** Donde dice `roles.py[...]` para config del usuario →
  `~/.orq/config.toml`. Ejemplos con nombres genéricos. Sección "Configuración" corta que apunte a
  `assets/config.example.toml`.
- [x] **Paso 3 — planes de PLAN-001.** Reemplazar nombres reales por los genéricos manteniendo el
  sentido técnico de cada hallazgo (p. ej. "un repo Quarkus de 157 commits adelante en un worktree").
- [x] **Paso 4 — `README.md`.** Qué es, requisitos (Claude Code, Python ≥ 3.11, git), instalación
  (`git clone` en `~/.claude/skills/orquestar-sesiones`, copiar el ejemplo a `~/.orq/config.toml`),
  primer uso (`need` → `spawn`), y la nota de DD-5 sobre SHAs en `plans/`.
- [x] **Paso 5 — `LICENSE`.** MIT, año 2026, titular `snaven10`.
- [x] **Paso 6 — `.gitignore`.** `__pycache__/`, `*.bak-*`.

## Criterios de aceptación
- [x] `git grep -n -i` con la lista privada de identificadores del cliente, máquinas, IP y rutas del HOME vacío
  (salvo `LICENSE`, que nombra al titular).
- [x] `python3 -m py_compile assets/orq.py` OK; `git diff --stat` de `orq.py` solo en líneas de comentario/docstring/mensaje.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:** done
- **Resumen:** `orq.py`: los hints de `status`/`spawn`/scout dejan de nombrar máquinas fijas y salen de la
  config (nuevo campo de máquina `ssh_attach`, lista o string, con fallback a `ssh`; la sugerencia
  "casi seguro de <otra máquina>" nombra la única remota si hay una; el scout imprime la máquina de
  su arquetipo; el hint `scp` usa la máquina activa). Comentarios/docstrings, `SKILL.md` (sección
  "Configuración", licencia MIT), `references/escenarios.md` y los planes quedan con nombres
  inventados. Nuevos: `README.md`, `LICENSE` (MIT 2026), `.gitignore`.
- **Archivos tocados:** `assets/orq.py`, `assets/config.example.toml`, `SKILL.md`,
  `references/escenarios.md`, `plans/**`, `README.md`, `LICENSE`, `.gitignore`.
- **Verificado por:** regresión contra la skill viva (`captura.sh`, mismo path con "claude"): solo difiere
  `--help`; `status.txt` idéntico. `cfg_igual`: solo `recursos_exclusivos.devctx_index` y el campo nuevo
  `ssh_attach` de una máquina del usuario. `py_compile` OK; `tomllib` carga el ejemplo y la config del
  usuario; `--help`/`need`/`status` con HOME vacío sin traceback; `git grep` de identificadores vacío
  (salvo el handle del autor en `LICENSE`, `SKILL.md` y este plan).
