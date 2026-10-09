---
name: orquestar-sesiones
description: >
  Levanta sesiones Claude especializadas en otra máquina (o local) para trabajar en paralelo,
  proponiendo qué agentes hacen falta y pidiendo aval antes de gastar.
  Trigger: el usuario pide levantar sesiones, trabajar en paralelo, orquestar agentes,
  repartir tareas entre micros, o correr review/qa/validación sobre trabajo en curso.
license: MIT
metadata:
  author: snaven10
  version: "1.0"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__devctx__recall, mcp__devctx__search, mcp__devctx__remember
---

## Qué es esto

Sos el **orquestador**. Cuando levantás sesiones, esas sesiones son tuyas: vos las
coordinás, vos cosechás su resultado, vos cerrás el ciclo.

El script `assets/orq.py` hace el trabajo mecánico. Esta skill es el **contrato** de
cómo usarlo sin cagarla.

## Regla de oro

**NUNCA levantés una sesión sin que el usuario haya visto la propuesta y dado el aval.**

No es una sugerencia de cortesía. Cada spawn cuesta **$0.09–0.16 solo en arrancar**
(20–41k tokens de preámbulo: agente + CLAUDE.md + protocolos). Cinco sesiones mal
dimensionadas son un dólar tirado antes de que nadie escriba una línea.

El script lo hace imposible: `spawn` sin token válido sale con `rc=2`. No hay flag de
escape. Si te ves pensando "esta es obvia, la levanto directo" — pará. No lo es.

## Flujo

### 1. Resolver qué hace falta

`orq` es un wrapper en `~/.local/bin/orq`. Se invoca desde cualquier directorio.
**Las sesiones corren en la máquina `maquina_default` de tu config** (o `local`). Para otra
máquina declarada: `orq --host <maquina> ...` o `ORQ_HOST=<maquina>` — si tiene `ssh`, habla
por SSH y, sin devctx allá, los workers NO guardan aprendizajes en vivo.

La concurrencia por máquina (`concurrencia`) se declara en la config: dimensionala según la
RAM libre (cada sesión ≈1 GB + 2-3 GB si compila) y el rate limit de tu cuenta.

## Configuración

Tu configuración vive en **`~/.orq/config.toml`** (fuera del código). Se aplica encima de
los defaults genéricos de `assets/roles.py` (merge profundo). Partí de
[assets/config.example.toml](assets/config.example.toml), que documenta cada campo: máquinas,
workspaces, specialists, recursos exclusivos. Sin archivo, orq corre en `local` y usa el repo
git del cwd como workspace. `ORQ_CONFIG=/ruta/otra.toml` prueba otra config sin tocar la tuya.

**Workspace.** La sección `[workspaces.*]` de tu config declara dónde se trabaja. Hay dos tipos:
`multi` (un directorio con varios repos adentro; los targets son los subdirectorios con
`.git`) y `repo` (un repo suelto; el target es el propio repo). Ejemplo: `mi-empresa` (multi,
`~/proyectos/mi-empresa`) y `herramienta` (repo).

Cómo se elige, en este orden: `orq --ws <nombre|ruta> ...` → `ORQ_WS` → el workspace
declarado cuyo `path` contiene el cwd (gana el más largo) → **el repo git del cwd, como
workspace implícito** → `workspace_default` **con aviso** en stderr. El token guarda el `ws`,
así que `spawn` lo respeta aunque cambies de directorio entre `need` y `spawn`.

**Cualquier repo funciona sin declararlo.** Un repo no declarado se registra solo como
workspace `repo` en `~/.orq/workspaces.json` (avisa con `➕ workspace implícito`). Un
worktree se resuelve a su repo principal. Declaralo en tu config solo si necesita `add_dir`,
`ruido` o recursos propios. Los recursos exclusivos pueden llevar `solo_ws: ["mi-empresa"]`:
un "seed" en otro repo no bloquea la base de QA de ese workspace.
`--add-dir` solo se pasa si el workspace declara `add_dir`; en un `repo`
el agente de proyecto resuelve por cwd y no hace falta.

```bash
orq need "<lo que se va a trabajar>"                    # ws por cwd / default
orq --ws herramienta need "<lo que se va a trabajar>"
orq --ws ~/personal/otro-repo need "<lo que se va a trabajar>"   # ruta: se registra sola
```

### 2. Presentarla COMPLETA al usuario

Pegá la tabla tal cual. No la resumás, no la "mejorés". El usuario tiene que ver:

- Qué specialist se usa para cada sesión **y de qué scope salió**
- Qué sesiones se **reusan** (dormidas, con su contexto) vs cuáles se **crean**
- Qué worktrees se van a crear
- Qué recursos quedan bloqueados en exclusiva
- El costo estimado
- Qué tasks quedan afuera y por qué

**Después de pegar la tabla, PARÁ.** No sigas con código, ni explicaciones, ni acciones.
Esperá que el usuario verifique, modifique o cancele.

### 3. Si falta un specialist: 3 escalones

`need` resuelve cada sesión en este orden y te dice en qué escalón cayó (columna ORIGEN).
**Nunca se autoasigna nada que el usuario no haya confirmado**, y **nunca hay agentes
globales automáticos**: un agente de stack global existe solo si el usuario elige `[g]` al guardarlo.

**Escalón 1 — confirmado.** Está en `~/.orq/specialists.json` o en la tabla `[specialists]` de tu config (o de `roles.py`)
**y el `.md` existe** en un dir alcanzable. Se usa. No hacés nada.

**Escalón 2 — candidatos en disco.** El mapeo no existe, pero hay agentes `.md` (del repo,
del workspace o de `~/.claude/agents`) con afinidad ≥ umbral con las señales del target
(`pom.xml`, `angular.json`, `go.mod`…). `need` muestra el top 3 con puntaje y tags:

```
java-backend-specialist   0.83  [java, quarkus, oracle]
```

Qué hacés vos: **pegás los candidatos con su puntaje y tags, y PARÁS.** Que el usuario
confirme cuál (o ninguno). Recién con su OK:

```bash
orq agent use <nombre> <arquetipo>@<target>     # target * = todos
```

Queda en `specialists.json`; la próxima vez es escalón 1.

**Escalón 3 — scout.** No hay candidatos. `need` agrega "SCOUTS PROPUESTOS", un scout por
faltante, con su costo. El scout es una sesión `claude -p` de solo lectura (en la máquina del
arquetipo `scout`, con devctx) que investiga el repo y deja un **borrador**; no escribe nada más. Qué hacés vos:

1. Presentás el scout **con su costo** y **PARÁS por el aval**. Cuesta plata: es un spawn.
2. Con el aval: `orq scout <arq>@<target> --token T-xxxxxx [--only S1]`. Un scout por
   invocación. Se marca hecho en el token y **no se repite** con ese token; el token en sí
   no se consume, sirve después para `spawn`.
3. Leés el draft (`~/.orq/drafts/<name>.md`) y las razones (`<name>.razones.md`).
4. Presentás el agente **COMPLETO** (frontmatter + cuerpo), las razones con su evidencia, y
   la tabla de scopes válidos **para ese ws**, y **PARÁS a preguntar el scope**.
5. Solo con la respuesta:

```bash
orq agent save <draft> <arquetipo>@<target> --scope p|m|g [--force]
```

**El scope SIEMPRE se pregunta. No hay default**: sin `--scope`, `save` sale con `rc=2`.
Mostralo aunque parezca obvio; el usuario decide, vos no.

| Opción | Dónde | Resuelve desde | Costo | Ws |
|---|---|---|---|---|
| `[p]` proyecto | `<repo>/.claude/agents/` | cwd en ese repo | ninguno; queda sin commitear (`save` no commitea) | multi y repo |
| `[m]` monorepo | `<ws.agents>/` (ej. `~/proyectos/mi-empresa/.claude/agents/`) | **solo con `--add-dir`** | el flag es obligatorio | **solo multi** con `add_dir` |
| `[g]` global | `~/.claude/agents/` | cualquier cwd | contamina todos tus proyectos | multi y repo |

`save` valida `name` (kebab-case), `description` y `model` ∈ sonnet|opus|haiku|fable
(obligatorio), no pisa un archivo sin `--force`, y avisa si otro agente homónimo de scope
más cercano lo tapa. Sin `<arq>@<target>` guarda el archivo pero **no registra el mapeo**
(después hay que correr `orq agent use`).

**De dónde sale el contenido del draft.** Las fuentes de siempre las usa ahora el **scout**, no
vos a mano: DevCtxEngine (`search`/`recall`/`build_context`), memoria histórica
(`~/.claude/projects/*/memory/*.md`: los nombres de archivo son oro), context7 (docs del
stack) y la skill `claude-code-setup:claude-automation-recommender` (genérica, razona por
señales de stack, read-only). Si el scout devuelve algo sin `model:` te lo avisa: no lo
guardes así.

### 4. Definir el árbol y levantar

**El orquestador NO decide dónde trabaja cada sesión. Clasifica y pregunta.**

| Qué se va a hacer | Árbol | ¿Se pregunta? |
|---|---|---|
| Auditar lo **ya commiteado** | worktree detached @ SHA | no |
| Auditar lo **sin commitear** | **árbol principal — obligatorio** | no, no hay opción |
| Implementar **1 tarea** | a definir | **sí**: ¿rama actual `X` / otra / worktree? |
| Implementar **N en paralelo** | worktree + rama nueva por tarea | **sí**, si no colisionan en archivos |

El único caso sin opción es por física de git: **`git worktree add` da un checkout
limpio del commit; los cambios sin commitear viven en el índice y el working tree del
árbol ORIGINAL y no se copian.** Auditar WIP en un worktree nuevo es auditar el aire.

La rama nueva se ramifica de la **rama actual del árbol**, no de `development`.

`spawn` rechaza con `rc=2` si queda una pregunta sin responder (`--arbol`) o si se
crearían worktrees sin política de destrucción (`--destruccion`). Esa política se
pregunta **al crear cada worktree** y se guarda por worktree:

```
[nunca]      no se borra nunca; `orq reap` lo lista y vos decidís
[si_limpio]  `orq reap --force` lo borra si está limpio (la rama solo si además está mergeada)
[tras_merge] `orq reap --force` lo borra si está limpio Y su rama ya entró al HEAD del
             checkout principal; borra también la rama (`branch -d`)
```

Nada se destruye al terminar la sesión: la política se aplica cuando corrés
`orq reap --force` (sin `--force` solo muestra qué es borrable). Un worktree con una
sesión viva adentro **nunca** se toca — recién creado está limpio y su rama, sin
commits, es ancestro de HEAD: pasaría por "mergeado". Y `worktree remove` va sin
`--force` de git: si alguien lo ensució entre el chequeo y el borrado, se niega.

```bash
orq spawn --token T-xxxxxx [--only N] [--sin-specialist N[,M]] \
    [--arbol rama_actual|otra:<nombre>|worktree] [--destruccion nunca|si_limpio|tras_merge]
```

**Gate de specialists.** Antes de lanzar nada, `spawn` re-resuelve cada fila (si entre
`need` y `spawn` se confirmó un match o se guardó un agente, se usa solo). Si alguna sesión
sigue sin specialist, sale con `rc=2`, **no lanza ninguna** y lista las tres salidas:
`agent use`, `scout` → `agent save`, o `--sin-specialist N[,M]` (N = número de fila de
`need`, igual que `--only`). Ese flag es la aceptación explícita, por fila, de una sesión
genérica sin criterio de dominio: se lo pedís al usuario, no lo ponés por tu cuenta.

`orq reap` lista worktrees y jobs zombie. **Nunca borra solo**: `orq reap --force` aplica
la política de destrucción de cada worktree y limpia los jobs zombie del registro.

**Cierre de tasks en workspaces `repo`.** El plan vive dentro del repo, así que el
prompt le pide al worker que cierre la task en la copia del plan de **su worktree** y lo
commitee en su rama: el cierre viaja con el merge y el árbol principal queda limpio.
En `multi` (`~/proyectos/mi-empresa`) `plans/` no es parte de ningún repo y se escribe donde siempre.

### 5. Cosechar y evolucionar

Al cerrar, `orq harvest` convierte el resultado de cada sesión en un
`~/.claude/pending-agent-updates.json` **con contenido real** (el hook nativo solo
escribe un marcador vacío y lleva meses estancado).

Después: `/agent-evolve` — presenta los cambios al usuario y escribe los
`## Learned Patterns` de cada agente que participó.

Los workers en una máquina sin devctx **no lo tienen**: sus aprendizajes solo vuelven por el
resultado de `orq`. Si no cosechás, se pierden.

## Trampas verificadas

**En un workspace `multi` con `add_dir`, el flag es obligatorio** (ejemplo:
`--add-dir ~/proyectos/mi-empresa`). Ese directorio no es un repo git; cada proyecto es su propio repo. El
escaneo de agentes sube desde el cwd hasta la **raíz del repo** y se detiene ahí — nunca
llega a `~/proyectos/mi-empresa/.claude/agents/`. Sin el flag: `--agent 'java-backend-specialist' not found`,
y **cae a `general-purpose` en silencio**: una sesión que parece funcionar y entrega trabajo
sin criterio de dominio. `orq` lo pasa solo si el ws lo declara; en un `repo` no aplica.

**Nombre mapeado sin `.md` = faltante.** Que un nombre figure en la config o en el overlay
no significa que exista. Si el archivo no está, el resolver lo marca faltante con aviso y el
gate de `spawn` frena (también en `need --plan`, si el PLAN declara un specialist inexistente).

**El catálogo se lee del disco LOCAL**, aunque uses `--host <maquina>`: no mira los agentes que
haya en la remota. Si el agente solo existe allá, `orq` lo va a dar por faltante.

**`ORQ_CLAUDE` es solo para tests**: reemplaza el binario de `claude` (para probar con uno
falso). No lo uses en operación real.

**SSH a una máquina remota puede necesitar `ClearAllForwardings`.** Si tu `~/.ssh/config` tiene
`RemoteForward` + `ExitOnForwardFailure yes`: si el puerto está ocupado, la conexión
entera muere.

**`claude` no está en el PATH de SSH no-interactivo en una máquina remota.** Ruta absoluta:
`~/.local/bin/claude`.

**El prompt va por stdin**, nunca como argumento — el anidamiento de comillas del SSH
se lo come.

**`attach` a una sesión TERMINADA la revive.** Verificado: una sesión `done` de 2 horas
apareció como "hace 3min" después de engancharse. Y al salir del attach, Claude **no
cierra el SSH: abre una sesión NUEVA** en el cwd del login (`~`), que además pide confiar
en esa carpeta y corre con el modelo por defecto, sin agente ni proyecto. Para una sesión
que ya terminó se usa `claude logs <id>`, que no revive nada. Y el comando de attach
siempre lleva `cd <repo> &&` delante, para que ese fallback aterrice en el repo y no en `~`.

**Ctrl+C dos veces NO mata la sesión remota**, solo te desengancha del attach: la sesión
sigue viva. Para matarla es `claude stop <id>`, por id, nunca por patrón.

**`--session-id` solo CREA.** Para seguir una sesión existente es `--resume`.

**En headless todo lo que pediría permiso se deniega solo.** Cada arquetipo declara sus
tools en `roles.py`.

## Nunca

- Levantar sesiones sin aval del usuario.
- Confiar en el nombre de un worktree para saber en qué rama está. Siempre `git rev-parse`.
- Asignar un worktree sin `git status --porcelain` antes.
- Compartir un worktree entre dos agentes activos.
- Correr ETL, cargas masivas a un gestor documental, migraciones de base de datos o `index_repo --full` en paralelo.
  Son exclusivos **por recurso**, no por repo: dos worktrees limpios no te salvan.
- Matar procesos por patrón (`pkill -f`). Solo por PID que vos lanzaste.
- Confiar en `Estado: done` de un archivo TASK. En un corpus real de 131 `done`, solo 3 tenían el Result
  Contract lleno. Verificá contra git (SHAs, archivos), no contra el markdown.

## Recursos

- **Script**: [assets/orq.py](assets/orq.py) · **Política**: [assets/roles.py](assets/roles.py)
- **Los 17 escenarios y su mitigación**: [references/escenarios.md](references/escenarios.md)
