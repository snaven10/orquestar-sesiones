# TASK-011 — Verificación antes de publicar

- **Plan:** PLAN-002 — config externa y publicación
- **Especialista:** orquestador (QA propia, no delegada)
- **Proyecto:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`), rama de integración
- **Depende de:** TASK-010
- **Estado:** `done`

---

## Objetivo
Probar DD-4 (sin regresión con la config del usuario) y DD-2 (funciona sin config) antes de merge.

## Pasos
- [ ] **Paso 1** — repetir `antes-002/COMANDOS.txt` en `despues-002/` y diffear. Solo pueden
  cambiar token, fecha y el texto de mensajes que TASK-010 cambió a propósito.
- [ ] **Paso 2** — HOME vacío: `--help`, `need` y `plan` en un repo git temporal con un plan
  sintético; error claro fuera de un repo.
- [ ] **Paso 3** — `config.example.toml` copiado tal cual como config: carga sin error.
- [ ] **Paso 4** — mutaciones en el merge (dict vs lista, ausencia de `maquina_default`) en una copia
  scratch: cada una tiene que romper algún paso de arriba.
- [ ] **Paso 5** — `git grep` de TASK-010 vacío; merge `--no-ff` a `main`.

## Criterios de aceptación
- [ ] Diffs explicados línea por línea en el Resultado.
- [ ] Merge en `main` y `orq` instalado sigue funcionando para despachar (un `need` real).

## Resultado
<!-- SE LLENA AL CERRAR (estado done/skipped). Vacío mientras esté pending. -->
- **Estado final:** `done`
- **Resumen:** QA del orquestador sobre la rama `feature/plan-2-task-009` (TASK-009 + TASK-010). Sin regresión con la config del usuario; funciona sin config; el árbol no nombra al cliente ni a las máquinas del usuario.
- **Archivos tocados:** ninguno de código (solo este archivo y la tabla del master).
- **Verificado por:**
  - Regresión: `captura.sh` con el `orq.py` de `main` y el de la rama (copiado a una ruta con "claude" para igualar el auto-match de `pgrep` del preflight), uno detrás del otro. Único archivo distinto: `help.txt` (`--host HOST` sin `choices`, textos de `--host`/`--ws`), cambio pedido en TASK-009. `status.txt`, los 4 `need` y los 2 `plan`, idénticos salvo tokens.
  - Config efectiva vs `roles.py` viejo (`cfg_igual.py`): solo difieren `maquinas.remota` (campo nuevo `ssh_attach`, TASK-010) y `recursos_exclusivos.devctx_index` (motivo genérico).
  - Mutaciones en copias scratch: merge no recursivo → 174 líneas de diff; host por defecto ignorando `maquina_default` → 105; merge que no pisa claves existentes (`setdefault`) → 0 en capturas pero lo detecta `cfg_igual` (`arquetipos.scout.maquina`). Por eso la verificación usa las dos.
  - HOME vacío + repo git temporal con plan sintético: `--help`, `need`, `plan 1`, `status` rc 0 sin traceback; fuera de un repo y sin config, rc 2 con mensaje. `config.example.toml` como `ORQ_CONFIG`: `need` rc 0.
  - `_ssh_attach`: `'ssh remota-tty'` con la config del usuario; sin `ssh_attach`, el `ssh` unido.
  - `git grep` amplio (cliente, repos, planes, máquinas, IP, `/home/`) vacío; quedan palabras técnicas genéricas (Quarkus, Oracle, "plantillas").
- **Riesgos abiertos / siguiente:** el fallback de `_ssh_attach` usa el `ssh` de `run` (con `BatchMode`, sin `-t`); para attach interactivo conviene declarar `ssh_attach` (el ejemplo lo documenta). No ejercido con un job real en otra máquina.
