# TASK-010 — Texto genérico, README y LICENSE MIT

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** general-purpose (sonnet)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), worktree de orq
- **Depende de:** TASK-009
- **Estado:** `pending`

---

## Objetivo
Ningún archivo versionado nombra al cliente, sus repos, sus planes ni las máquinas del usuario.
Los ejemplos pasan a nombres inventados y el repo trae README de instalación y licencia.

## Contexto verificado
- Menciones actuales: `assets/orq.py` (10, comentarios/docstrings, p. ej. el docstring con
  `api-backend (`/ruta/`)`), `SKILL.md` (9, incluye `--add-dir ~/mi-empresa` y referencias a
  `roles.py["workspaces"]`), `references/escenarios.md` (6), `plans/PLAN-001-*` (~40).
- Otros identificadores en el árbol: `remota`, `snaven10`, la IP de Tailscale de remota.

## Pasos
- [ ] **Paso 1 — código.** Comentarios y docstrings de `orq.py` con ejemplos genéricos
  (`mi-empresa`, `api-backend`, `web-frontend`). El comportamiento no cambia: solo texto.
- [ ] **Paso 2 — `SKILL.md` y `references/`.** Donde dice `roles.py[...]` para config del usuario →
  `~/.orq/config.toml`. Ejemplos con nombres genéricos. Sección "Configuración" corta que apunte a
  `assets/config.example.toml`.
- [ ] **Paso 3 — planes de PLAN-001.** Reemplazar nombres reales por los genéricos manteniendo el
  sentido técnico de cada hallazgo (p. ej. "un repo Quarkus de 157 commits adelante en un worktree").
- [ ] **Paso 4 — `README.md`.** Qué es, requisitos (Claude Code, Python ≥ 3.11, git), instalación
  (`git clone` en `~/.claude/skills/orquestar-sesiones`, copiar el ejemplo a `~/.orq/config.toml`),
  primer uso (`need` → `spawn`), y la nota de DD-5 sobre SHAs en `plans/`.
- [ ] **Paso 5 — `LICENSE`.** MIT, año 2026, titular `snaven10`.
- [ ] **Paso 6 — `.gitignore`.** `__pycache__/`, `*.bak-*`.

## Criterios de aceptación
- [ ] `git grep -n -i -E 'mi-empresa|org|remota|snaven10/|100\.112|_BackEnd|_FrontEnd|-srv\b|PLAN-1[0-9]{2}'` vacío
  (salvo `LICENSE`, que nombra al titular).
- [ ] `python3 -m py_compile assets/orq.py` OK; `git diff --stat` de `orq.py` solo en líneas de comentario/docstring/mensaje.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**
