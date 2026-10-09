# TASK-012 — Reescribir el historial y publicar

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** orquestador
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`)
- **Depende de:** TASK-011 y PLAN-009 TASK-021 del dashboard (misma lista de reemplazos)
- **Estado:** `done`

---

## Objetivo
Un repo público en GitHub cuyo historial completo no contiene nada del cliente ni de las máquinas
del usuario (DD-5).

## Decisiones del usuario
- Licencia: **MIT** (confirmado 2026-10-09).
- Correo de autor en los commits: **el propio** (confirmado 2026-10-09). Sin `--mailmap`.
- Visibilidad: pública.

## Pasos
- [ ] **Paso 1 — respaldo.** `git clone --mirror` a `~/respaldos/orquestar-sesiones-pre-publicacion.git`.
- [ ] **Paso 2 — herramienta.** Bajar `git-filter-repo` de una release fijada al scratchpad.
- [ ] **Paso 3 — reemplazos.** `reemplazos.txt` compartido con el dashboard (nombres del cliente,
  repos, planes, máquinas, IP, rutas del HOME). En un clone fresco:
  `filter-repo --replace-text reemplazos.txt --replace-message reemplazos.txt`.
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
- **Estado final:** `done`
- **Resumen:** historial reescrito con `git-filter-repo` 2.47.0 (misma lista que el dashboard), README nuevo, publicado en https://github.com/snaven10/orquestar-sesiones. El repo local usa la credencial personal (`credential.helper` local) porque vive fuera de `~/personal/`.
- **Archivos tocados:** todo el historial (30 commits reescritos); `README.md`.
- **Verificado por:** `git log --all -p` (código, diffs, mensajes, autor) del repo reescrito contra la lista privada de identificadores: 0 coincidencias en los dos repos. Árbol final comparado contra el original: solo cambian textos de docs (máquinas y ramas de ejemplo). Tests en el repo reescrito (dashboard: Go en verde, node 53/53; orq: `py_compile`). Objetos viejos eliminados del repo local (`reflog expire` + `gc --prune=now`; un SHA viejo ya no resuelve). Repos creados por la API de GitHub con la credencial personal, públicos, licencia MIT detectada, topics cargados, imagen del README servida (HTTP 200).
- **Desviaciones:** la primera pasada de reemplazos cambiaba la palabra común "partida(s)" y rompía comentarios legítimos; se acotó a las frases del dominio y se rehízo. README creativo nuevo pedido por el usuario al publicar.
- **Riesgos abiertos / siguiente:** los SHAs citados en `plans/` son de antes de la publicación (nota en el README). Respaldos completos pre-publicación en `~/respaldos/` (locales, nunca se suben).
