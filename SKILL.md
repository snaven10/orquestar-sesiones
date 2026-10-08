---
name: orquestar-sesiones
description: >
  Levanta sesiones Claude especializadas en remota (o local) para trabajar en paralelo,
  proponiendo qué agentes hacen falta y pidiendo aval antes de gastar.
  Trigger: el usuario pide levantar sesiones, trabajar en paralelo, orquestar agentes,
  repartir tareas entre micros, o correr review/qa/validación sobre trabajo en curso.
license: Apache-2.0
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

`orq` es un wrapper en `~/.local/bin/orq`. Se invoca desde local, desde cualquier directorio.
**Las sesiones corren en local por defecto** (local, con devctx, concurrencia 2). Para remota:
`orq --host remota ...` o `ORQ_HOST=remota` — ahí habla por SSH y los workers NO tienen devctx.

Por qué 2 en local: ~24 GB libres con el trabajo propio; cada sesión ≈1 GB + 2-3 GB si compila
Quarkus; y PLAN-043 DD-7 serializa extracciones, así que el 2º slot es review/inventario.

```bash
orq need "<lo que se va a trabajar>"
```

Devuelve la propuesta: arquetipos, targets, specialists, worktrees, locks de recurso,
costo estimado, y **qué se queda afuera y por qué**.

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

### 3. Si falta un specialist

El resolver te va a marcar `❌ sin specialist`. Ahí **proponés cómo debería quedar el
agente**, armado de estas fuentes en orden:

1. **DevCtxEngine** — `search` y `recall` sobre el target. Es la fuente más rica.
2. **Memoria histórica** — `~/.claude/projects/*/memory/*.md` (la auto-memory vieja,
   apagada para escribir pero legible). Los nombres de archivo son oro.
3. **context7** — docs del stack detectado, si el MCP está disponible.
4. **claude-automation-recommender** — skill del plugin `claude-code-setup`.
   Es **genérica**: razona por señales de stack, no por dominio de negocio. Sirve para
   repos sin historia. Es read-only, no escribe nada.

Proponé el frontmatter completo:

```yaml
name: tickets-backend-specialist
description: ...          # cuándo delegarle
model: sonnet             # sonnet | opus | haiku | fable
tools: Read, Grep, Glob, Edit, Write, Bash
disallowedTools: ...      # para auditores: Write, Edit
mcpServers: [devctx]      # evita el race del MCP compartido
permissionMode: default
```

Y **SIEMPRE preguntá dónde guardarlo**, mostrando el scope detectado y su costo:

| Opción | Dónde | Resuelve desde | Costo |
|---|---|---|---|
| `[p]` proyecto | `<repo>/.claude/agents/` | cwd en ese repo | ninguno |
| `[m]` monorepo | `~/mi-empresa/.claude/agents/` | **solo con `--add-dir ~/mi-empresa`** | el flag es obligatorio |
| `[g]` global | `~/.claude/agents/` | cualquier cwd | contamina todos tus proyectos |

**Mencionalo siempre, aunque parezca obvio.** El usuario decide, vos no.

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
[nunca]      no se borra solo; `orq reap` los lista y vos decidís
[si_limpio]  al terminar la sesión, si no quedan cambios sin commitear
[tras_merge] cuando su rama ya está integrada
```

```bash
orq spawn --token T-xxxxxx [--only N] \
    [--arbol rama_actual|otra:<nombre>|worktree] [--destruccion nunca|si_limpio|tras_merge]
```

`orq reap` lista worktrees y jobs zombie. **Nunca borra solo.**

### 5. Cosechar y evolucionar

Al cerrar, `orq harvest` convierte el resultado de cada sesión en un
`~/.claude/pending-agent-updates.json` **con contenido real** (el hook nativo solo
escribe un marcador vacío y lleva meses estancado).

Después: `/agent-evolve` — presenta los cambios al usuario y escribe los
`## Learned Patterns` de cada agente que participó.

Los workers en remota **no tienen devctx**: sus aprendizajes solo vuelven por el
resultado de `orq`. Si no cosechás, se pierden.

## Trampas verificadas

**`--add-dir ~/mi-empresa` es obligatorio.** `~/mi-empresa` no es un repo git; cada proyecto MI-EMPRESA
es su propio repo. El escaneo de agentes sube desde el cwd hasta la **raíz del repo** y
se detiene ahí — nunca llega a `~/mi-empresa/.claude/agents/`. Sin el flag:
`--agent 'java-backend-specialist' not found`, y **cae a `general-purpose` en silencio**:
una sesión que parece funcionar y entrega trabajo sin criterio de dominio. El script
verifica que el agente resolvió; no confíes en que el flag esté puesto.

**SSH a remota necesita `ClearAllForwardings`.** El `~/.ssh/config` tiene
`RemoteForward 2223` + `ExitOnForwardFailure yes`: si el puerto está ocupado, la conexión
entera muere.

**`claude` no está en el PATH de SSH no-interactivo en remota.** Ruta absoluta:
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
- Correr ETL, carga a gestor-docs, migración Oracle o `index_repo --full` en paralelo.
  Son exclusivos **por recurso**, no por repo: dos worktrees limpios no te salvan.
- Matar procesos por patrón (`pkill -f`). Solo por PID que vos lanzaste.
- Confiar en `Estado: done` de un archivo TASK. De 131 `done`, 3 tenían el Result
  Contract lleno. Verificá contra git (SHAs, archivos), no contra el markdown.

## Recursos

- **Script**: [assets/orq.py](assets/orq.py) · **Política**: [assets/roles.py](assets/roles.py)
- **Los 16 escenarios y su mitigación**: [references/escenarios.md](references/escenarios.md)
