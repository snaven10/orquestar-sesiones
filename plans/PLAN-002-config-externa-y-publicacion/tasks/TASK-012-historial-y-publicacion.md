# TASK-012 — Reescribir el historial y publicar

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** orquestador
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`)
- **Depende de:** TASK-011 y PLAN-009 TASK-021 del dashboard (misma lista de reemplazos)
- **Estado:** `pending`

---

## Objetivo
Un repo público en GitHub cuyo historial completo no contiene nada del cliente ni de las máquinas
del usuario (DD-5).

## Decisiones del usuario
- Licencia: **MIT** (confirmado 2026-10-09).
- Correo de autor en los commits: **pendiente** (propio vs `noreply` de GitHub vía `--mailmap`).
- Visibilidad: pública.

## Pasos
- [ ] **Paso 1 — respaldo.** `git clone --mirror` a `~/respaldos/orquestar-sesiones-pre-publicacion.git`.
- [ ] **Paso 2 — herramienta.** Bajar `git-filter-repo` de una release fijada al scratchpad.
- [ ] **Paso 3 — reemplazos.** `reemplazos.txt` compartido con el dashboard (nombres del cliente,
  repos, planes, máquinas, IP, rutas del HOME). En un clone fresco:
  `filter-repo --replace-text reemplazos.txt --replace-message reemplazos.txt` (+ `--mailmap` si aplica).
- [ ] **Paso 4 — verificación.** `git log --all -p | rg -i <patrón completo>` vacío;
  `git log --all --format='%an %ae %cn %ce'` según lo decidido; `py_compile` en el HEAD.
- [ ] **Paso 5 — GATE.** Mostrar al usuario: lista de reemplazos, conteo de commits, resultado del
  `rg`, README. **No se pushea sin su OK explícito.**
- [ ] **Paso 6 — publicar.** Crear el repo (público), `git push`, comprobar en la web que el repo
  muestra README y LICENSE. Reemplazar el repo local por el reescrito (o re-clonar) y verificar que
  `orq` instalado sigue funcionando.

## Riesgos
- Publicar es irreversible: forks y cachés. Por eso el gate del Paso 5.
- Una variante no listada se cuela → el `rg` del Paso 4 es sobre TODO el historial, con el patrón
  amplio, no solo sobre `main`.

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:**
- **Resumen:**
- **Archivos tocados:**
- **Verificado por:**
