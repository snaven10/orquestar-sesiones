# Política del orquestador. Módulo Python: cero dependencias, comentarios permitidos.
# Arquetipo = QUÉ hace. Target = DÓNDE. El target se DESCUBRE, nunca se declara acá.

CFG = {

    # Máquinas donde corren las sesiones. Default: solo esta (`local`). El usuario declara las
    # suyas en ~/.orq/config.toml y elige la default con `maquina_default`.
    "maquinas": {
        "local": {
            "ssh": [],                         # vacío = local: `bash -s` sin SSH
            "claude": "claude",                # el del PATH
            "concurrencia": 2,
            "tiene_devctx": False,
        },
    },

    # Workspaces: DÓNDE trabaja orq. Se declaran en ~/.orq/config.toml; sin declarar, el
    # workspace sale del repo git del cwd (implícito, se registra en ~/.orq/workspaces.json).
    #   multi: dir con varios repos hijos (los targets se descubren: subdirs con .git).
    #   repo:  un repo suelto; el target es el propio repo.
    "workspaces": {},

    "arquetipos": {
        "worker": {
            "descripcion": "implementa",
            "tools": ["Read", "Grep", "Glob", "Edit", "Write", "Bash"],
            "persist": True,                   # acumula contexto del repo
            "fork_tras_turnos": 50,            # se forkea y se resume vía devctx
        },
        "reviewer": {
            "descripcion": "audita el diff",
            "tools": ["Read", "Grep", "Glob", "Bash(git *)"],
            "disallowed": ["Write", "Edit"],   # un auditor que escribe deja de ser auditor
            "persist": False,                  # contexto limpio SIEMPRE: si recuerda reviews
                                               # viejos valida contra su opinión, no el código
        },
        "qa": {
            "descripcion": "levanta y prueba",
            "tools": ["Read", "Grep", "Glob", "Bash"],
            "persist": False,
            "exclusivo": ["puertos"],          # dos qa pelean por 8080/4200
        },
        "validator": {
            "descripcion": "contrasta PLAN vs código real",
            "tools": ["Read", "Grep", "Glob", "Bash(git *)"],
            "disallowed": ["Write", "Edit"],
            "persist": False,
        },
        "scout": {
            "descripcion": "investiga el repo y propone un agente",
            # solo lectura y solo consulta: el scout NO escribe nada. El draft lo escribe orq
            # y el agente lo escribe `orq agent save` con el scope que elija el usuario.
            "tools": ["Read", "Grep", "Glob", "Bash(git log*)", "Bash(ls*)",
                      # el CLAUDE.md global manda eza/fd/bat: sin esto se los niegan (scout real 2026-10-08)
                      "Bash(eza*)", "Bash(fd*)", "Bash(bat*)", "Skill",
                      "mcp__devctx__search", "mcp__devctx__recall", "mcp__devctx__build_context",
                      "mcp__context7__resolve-library-id", "mcp__context7__query-docs"],
            "disallowed": ["Write", "Edit"],
            "persist": False,
            "modelo": "sonnet",
            "maquina": "local",                # el scout necesita devctx: máquina con tiene_devctx
            "costo": [0.25, 0.45],             # USD estimados (1er scout real: $0.36, 17 turnos)
            "timeout": 600,
        },
    },

    # arquetipo@target -> specialist. Se declara en ~/.orq/config.toml.
    # Sin entrada => el resolver marca "sin specialist" y la skill propone crear uno.
    "specialists": {},

    # ── Match por afinidad (escalón 2 de la resolución de specialists, PLAN-001 DD-3) ──
    # Puntaje mecánico y determinístico: gratis, reproducible y, sobre todo, NUNCA autoasigna:
    # solo propone candidatos y el usuario confirma con `orq agent use`.
    "match_umbral": 0.5,

    # Archivos marcadores del repo -> tags de stack. `contiene` busca el texto (en minúsculas)
    # DENTRO del archivo y suma tags: así `pom.xml` distingue Quarkus de Spring sin parsear XML.
    "señales": [
        {"archivos": ["pom.xml", "build.gradle", "build.gradle.kts"], "tags": ["java"],
         "contiene": {"quarkus": ["quarkus"], "oracle": ["oracle"]}},
        {"archivos": ["angular.json"], "tags": ["angular"]},
        {"archivos": ["nx.json"], "tags": ["nx"]},
        {"archivos": ["go.mod"], "tags": ["go"]},
        {"archivos": ["Cargo.toml"], "tags": ["rust"]},
        {"archivos": ["pyproject.toml", "requirements.txt"], "tags": ["python"]},
        # package.json casi siempre acompaña a otro stack: por sí solo solo dice `node`
        {"archivos": ["package.json"], "tags": ["node"],
         "contiene": {"@angular/core": ["angular"], "\"react\"": ["react"],
                      "\"typescript\"": ["typescript"]}},
    ],

    # Cómo se reconoce cada tag en el texto (name + description) de un agente. Sin esto `go`
    # no matchearía a "Golang" y `node` no matchearía a "Node.js". Tag sin alias = él mismo.
    "tags_alias": {
        "go": ["go", "golang"],
        "node": ["node", "nodejs", "node.js", "npm"],
        "java": ["java", "jvm"],
        "python": ["python", "py"],
        "typescript": ["typescript", "ts"],
    },

    # El arquetipo también cuenta como señal: un `reviewer` pide un agente que revise.
    # Son prefijos de palabra ("review" matchea "reviews", "reviewer").
    "arquetipo_señales": {
        "reviewer": ["review", "audit"],
        "validator": ["audit", "validat", "verif"],
        "qa": ["qa", "test"],
    },

    # Recursos EXCLUSIVOS: el lock es por RECURSO, no por repo.
    # Dos worktrees perfectamente aislados igual se destruyen si tocan lo mismo.
    "recursos_exclusivos": {
        "devctx_index": {
            "motivo": "el índice de devctx se corrompe si dos sesiones reindexan a la vez",
            "detectar": ["index_repo", "reindex", "devctx index", "indexar"],
        },
    },

    "preflight": {
        "actividad_reciente_min": 30,   # reflog/procesos: señal de que alguien está trabajando
    },

    # ── Política de árbol (definida por el usuario, 2026-09-22) ──────────────
    #
    # El orquestador NO decide solo: clasifica el trabajo y PREGUNTA donde
    # corresponde. Solo hay un caso sin opción, y es por física de git.
    "politica_arbol": {

        # Auditar lo YA COMMITEADO: el commit existe, un worktree lo puede checkoutear.
        "auditar_commiteado": {
            "arbol": "worktree",
            "rama": "detached",         # fijado al SHA: revisión determinista y reproducible
            "preguntar": False,
        },

        # Auditar lo SIN COMMITEAR: `git worktree add` da un checkout LIMPIO del commit.
        # Los cambios sucios viven en el índice/working tree del árbol ORIGINAL y NO
        # se copian. Revisar en un worktree nuevo sería revisar el aire.
        "auditar_sin_commitear": {
            "arbol": "principal",
            "obligatorio": True,        # no es preferencia, es física de git
            "motivo": "el worktree nuevo no ve el working tree sucio del árbol original",
            "preguntar": False,
        },

        # Implementar UNA tarea: el usuario elige dónde.
        "implementar_simple": {
            "preguntar": True,
            "opciones": ["rama_actual", "otra_rama", "worktree_nuevo"],
        },

        # Implementar VARIAS en paralelo: worktree por tarea, rama nueva por tarea.
        # Excepción: si las tareas no tocan los mismos archivos, se pregunta si
        # igual se quiere el aislamiento.
        "implementar_paralelo": {
            "arbol": "worktree",
            "rama": "nueva_por_task",
            "base": "rama_actual",      # se ramifica de la rama ACTUAL del árbol, no de development
            "preguntar_si_no_colisionan": True,
        },
    },

    # Al CREAR un worktree se pregunta su política de destrucción y se guarda
    # POR worktree en ~/.orq/worktrees.json. No hay default global.
    "destruccion_worktree": {
        "nunca":       "no se borra solo; `orq reap` los lista y el usuario decide",
        "si_limpio":   "al terminar la sesión, si no quedan cambios sin commitear",
        "tras_merge":  "cuando su rama ya está integrada",
    },

    # 25+ variantes reales de estado en 1166 archivos TASK -> 5
    "normalizar_estado": {
        "pending":     ["pending", "Pendiente", "pendiente", "PENDING", "ready", "-"],
        "in_progress": ["in_progress", "in progress", "sigue", "parcial", "partial", "nace", "WIP"],
        "blocked":     ["blocked", "bloqueada", "BLOCKED"],
        "done":        ["done", "DONE", "Done", "completed", "COMPLETED", "implemented", "COMPLETADO"],
        "skipped":     ["skipped", "POSTPONED", "DESCARTADA", "CANCELLED", "descartada"],
    },

    # `Estado: done` NO es evidencia: de 131 `done`, 3 tenían el Result Contract lleno.
    "verificar_done_contra_git": True,
}
