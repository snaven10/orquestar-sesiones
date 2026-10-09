# Los 17 escenarios y su mitigación

Ninguno es hipotético. Cada uno se verificó en vivo en una máquina remota, está documentado en la
memoria de DevCtxEngine, o salió del corpus de 1166 archivos TASK en 151 PLANes.

## 🔴 Críticos — corrompen datos o trabajo

### 1. Sesión humana viva en el repo
**Visto en vivo, dos veces en una tarde.** Un repo de plantillas cambió de rama tres veces
en seis horas (`feat/ejemplo-b` → `feat/ejemplo-a` → `chore/numeros-medidos`).
Un `git checkout` del orquestador le rompe el árbol a quien está trabajando.
**Mitigación**: preflight lee reflog + procesos `claude` vivos. Actividad < 30 min →
worktree obligatorio, nunca el árbol principal.

### 2. Árbol sucio ajeno
**Visto en vivo**: Un repo frontend con 18 archivos sin commitear en `development`.
Un worker que arranca ahí los mezcla en su commit.
**Mitigación**: `git status --porcelain` antes de asignar. Política `refuse` por defecto.
Jamás `git add -A` (además prohibido por el CLAUDE.md del proyecto cuando hay archivos de entorno que no se commitean).

### 3. El nombre del worktree miente
Memoria: un worktree llamado `api-backend_development` **no estaba** en `development`; un revisor delegado
reportó commits faltantes que sí existían. Mismo patrón en `_qa`, `_dev` y similares.
**Mitigación**: `git rev-parse --abbrev-ref HEAD` en vivo, siempre. Al pasar contexto
entre agentes: **SHAs concretos**, nunca "mirá la rama X".

### 4. ETL / gestor documental no toleran concurrencia
Con `parallelism=2` en una carga masiva, **8% de registros fallan con 500** porque la resolución de colisión
de nombres no sobrevive contención. Se bajó a `parallelism=1`; el facade nunca se arregló.
Deja colas en `ERROR` con `intentos=3` que ya no se reintentan solas.
**Mitigación**: lock **por recurso**, no por repo. Dos worktrees limpios no te salvan.

### 5. El índice de devctx se corrompe por contención
Dos corrupciones históricas: `central.duckdb.CORRUPTO-1251` (2026-08-13) e
`index.duckdb.wal.CORRUPTO-1907` (2026-08-17), con 8 procesos MCP vivos + un
`index --full` encima. Tumba `search`/`recall` para **todas** las sesiones.
**Mitigación**: `index_repo --full` serializado por repo. Un solo escritor.

### 6. El MCP de devctx racea entre sesiones
Bindeado a `web-frontend`, las búsquedas devolvieron código de
`servicio-auth`: otra sesión pisó el "current project" del mismo
proceso MCP. Un `reviewer` puede auditar **otro repo sin saberlo**.
**Mitigación**: `mcpServers:` en el frontmatter del agente, un proceso por sesión.

### 7. Module Federation asimétrico
Dos PRs mergeados a `development` y **revertidos 45 minutos después**: `remoteEntry.mjs`
se servía mal en producción porque el cambio no llegó a todos los MFEs.
**Mitigación**: cualquier task que toque `webpack*.config.ts`, `module-federation.config.ts`
o `project.json` de más de un MFE va **secuencial**, nunca en paralelo.

### 8. El commit se traga ediciones de otro agente
Tras un merge, **4 tests arreglados por un subagente quedaron fuera del commit** porque
`git add` no los tomó. Se descubrió de casualidad.
**Mitigación**: un worktree por agente activo. Jamás compartido entre dos roles.

## 🟠 Altos — bloquean o degradan

### 9. Gate cross-repo: backend antes que frontend
Regla documentada del workspace: *"backend completa el contrato antes de que el frontend
lo consuma"*. Precedente de bug: el mapa `ROL_A_SUFIJOS` duplicado entre backend y
frontend se desincronizó (dos sufijos casi iguales, uno con una letra de menos), corregido dos veces.
**Mitigación**: Fase 0 secuencial — el orquestador fija el contrato y lo **inyecta** a
ambos workers. No lo negocian entre ellos.

### 10. La base de QA falla por red, no por código
500 intermitentes en QA por acquisition timeout de 5s cuando la conexión cae en un
worker-node con mal firewall. la base al 7.5% de uso.
**Mitigación**: antes de escalar un 500 intermitente como bug, revisar este patrón.
Un fan-out agresivo multiplica los falsos positivos.

### 11. `pkill -f` mata sesiones ajenas
Se mató por error el `nx serve shell` real del usuario creyendo que era huérfano
(los `node_modules` symlinkeados entre worktrees hacen que la ruta del binario no
identifique el proyecto).
**Mitigación**: matar solo por PID propio. Nunca por patrón de línea de comandos.

## 🔻 Estructurales — del formato de PLAN

### 12. Las dependencias son prosa
De 1166 TASK, 421 tienen `Depende de:`, pero con contenido como
`012, 004 · D-3 · 007 + 018 A si TASK-001 elige CLAVE_IDEMPOTENCIA` — condicionales a
decisiones sin tomar, sub-pasos de otra task (`027 P8`), y referencias cruzadas a otros
PLANes. 613 archivos usan el campo legacy `Dependencies:` con tres sintaxis para "ninguna".
**Mitigación**: **no se infiere el DAG.** Se lee `### Paralelismo` del master si existe;
si no, se propone y el usuario aprueba.

### 13. 25+ variantes de estado
`pending`, `` `pending ``, `Pendiente`, `sigue`, `nace`, `c`, `parcial`, `DONE`,
`implemented`, `POSTPONED`, `DESCARTADA`… para un vocabulario que el protocolo define en 5.
**Mitigación**: mapa de sinónimos en `roles.py`, nunca enum estricto sobre el string crudo.

### 14. `done` sin Result Contract
De 131 tasks en `done`, **3** tenían el Result Contract lleno.
**Mitigación**: `Estado: done` no libera dependientes. Se verifica contra git —
SHAs, archivos tocados, ramas — no contra el markdown.

## 🟢 De infraestructura

### 15. Colisión de puertos en QA
Una máquina remota sin contenedores ni puertos escuchando. Si `qa` levanta Quarkus o Angular,
toma 8080/4200; dos `qa` en paralelo pelean y el segundo muere.
**Mitigación**: `qa` declara `exclusivo: [puertos]`. No paraleliza como un `reviewer`.

### 16. Máquina remota sin devctx, sin hooks, sin allowlist
`~/.devctx` vacío. `settings.json` de 113 bytes: solo tema y notificaciones.
Los workers remotos van ciegos y sus aprendizajes **no pueden volver por `remember`**.
**Mitigación**: `orq harvest` es la única vía de retorno. Sin cosecha, se pierden.

### 17. Specialist faltante / workspace ajeno al principal
Verificado al sumar un segundo workspace (repo suelto): la config mapeaba
`reviewer` a `code-reviewer`, que ahí no existe; y un nombre mapeado sin `.md` hacía que
`claude --agent` no lo encontrara y cayera a `general-purpose` en silencio. En un repo sin
historia de agentes tampoco hay candidatos que proponer.
**Mitigación**: el mapeo se verifica contra el catálogo en disco (nombre sin `.md` =
faltante). Tres escalones: confirmado → candidatos por afinidad (`orq agent use`, el usuario
confirma) → scout con aval (`orq scout`) y `orq agent save --scope` con el scope siempre
preguntado. `spawn` frena con `rc=2` salvo `--sin-specialist N,M`.

---

## Bonus: el loop de evolución está roto

El hook nativo de `SessionEnd` escribe:

```json
{"needs_review":true,"ended_at":"2026-08-19T17:41:11Z","source":"session-end-marker"}
```

Sin el array `agents` que `agent-evolve` Mode 1 necesita. Y la condición es
`[ -f ... ] || printf ...` — **solo escribe si el archivo NO existe**. Como existe sin
procesar desde el 19 de agosto, cada cierre posterior no escribió nada.

`orq harvest` escribe el `agents` poblado de verdad. Después: `/agent-evolve`.
