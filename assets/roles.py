# Política del orquestador. Módulo Python: cero dependencias, comentarios permitidos.
# Arquetipo = QUÉ hace. Target = DÓNDE. El target se DESCUBRE, nunca se declara acá.

CFG = {

    "maquinas": {
        "local": {
            "ssh": [],                         # vacío = local: `bash -s` sin SSH
            "claude": "~/.local/bin/claude",
            # 20 cores / 47 GB, pero ~24 GB libres con el trabajo propio (node, java,
            # MCPs). Cada sesión ≈1 GB (claude + sus MCP) + 2-3 GB si compila/testea
            # Quarkus. Y PLAN-043 DD-7 serializa las extracciones: el 2º slot es para
            # review/inventario de solo lectura, no para un segundo implementador.
            "concurrencia": 2,
            "tiene_devctx": True,
        },
        "remota": {
            "ssh": ["ssh", "-o", "BatchMode=yes", "-o", "ClearAllForwardings=yes",
                    "-o", "ExitOnForwardFailure=no", "remota"],
            "claude": "~/.local/bin/claude",   # NO está en el PATH no-interactivo
            "concurrencia": 4,                 # 8 cores/31GB; el techo real es el rate limit
            "tiene_devctx": False,             # los aprendizajes vuelven por `orq harvest`
        },
    },

    # Workspaces: DÓNDE trabaja orq. Selección: `--ws` -> el ws cuyo `path` contiene el cwd
    # -> `workspace_default`. `path` es relativo al HOME de la máquina que corre las sesiones
    # (remota también tiene ~/mi-empresa), por eso se conserva el `~`.
    #   multi: dir con varios repos hijos (los targets se descubren: subdirs con .git).
    #   repo:  un repo suelto; el target es el propio repo.
    "workspaces": {
        "mi-empresa": {
            "path": "~/mi-empresa", "tipo": "multi",
            # `~/mi-empresa` NO es repo git: cada proyecto es su propio repo, así que el escaneo de
            # agentes se detiene en la raíz del repo hijo y nunca llega a ~/mi-empresa/.claude/agents/.
            # Sin este flag el agente NO resuelve y cae a general-purpose EN SILENCIO.
            "add_dir": "~/mi-empresa",
            "agents": "~/mi-empresa/.claude/agents",
            "plans": "~/mi-empresa/plans",
            "worktrees_en": "~/mi-empresa/.orq-trees",
            # tokens que no distinguen nada entre repos de MI-EMPRESA
            "ruido": ["mi-empresa", "srv", "backend", "microservice", "microservicio", "back", "end"],
            # las claves de ~/.orq/*.json de MI-EMPRESA son anteriores a los workspaces: no se migran
            "claves_sin_prefijo": True,
        },
        "claude-dashboard": {
            "path": "~/personal/claude-dashboard", "tipo": "repo",
            # repo suelto: sin add_dir (el agente de proyecto resuelve por cwd) y sus worktrees
            # fuera del repo para no ensuciarlo
            "worktrees_en": "~/.orq/trees/claude-dashboard",
        },
    },
    "workspace_default": "mi-empresa",

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
    },

    # arquetipo@target -> specialist en ~/mi-empresa/.claude/agents/
    # Sin entrada => el resolver marca "sin specialist" y la skill propone crear uno.
    "specialists": {
        "worker@api-backend":                     "java-backend-specialist",
        "worker@web-frontend":                    "angular-frontend-architect",
        "worker@qc-service":        "java-backend-specialist",
    # Worktrees que SON el árbol vigente, no duplicados: el código de Calidad
    # está 157 commits adelante en qc-service-dev, no en el checkout principal.
    "worker@qc-service-dev":                 "java-backend-specialist",
    "worker@web-frontend-qc":            "angular-frontend-architect",
        "worker@auth-service": "authentication-specialist",
        "worker@docs-service":              "docs-specialist",
        # Micros de mi-empresa (PLAN-043): mismo stack Quarkus reactive que el monolito.
        "worker@actos-srv":             "java-backend-specialist",
        "worker@clientes-srv":                      "java-backend-specialist",
        "worker@ajustes-srv":       "java-backend-specialist",
        "reviewer@*":                               "code-reviewer",
        # HUECOS CONOCIDOS que el resolver va a marcar:
        #   worker@api-plantillas · worker@tickets-srv · qa@* · validator@*
    },

    # Recursos EXCLUSIVOS: el lock es por RECURSO, no por repo.
    # Dos worktrees perfectamente aislados igual se destruyen si tocan lo mismo.
    "recursos_exclusivos": {
        "gestor-docs": {
            "motivo": "parallelism=2 -> 8% de registros fallan con 500 (colisión de nombres)",
            "detectar": ["gestor-docs", "carga masiva", "subida de documentos"],
        },
        "base_qa": {
            "motivo": "acquisition timeout 5s; fallos de RED que se leen como bug de código",
            "detectar": ["migracion", "migración", "ddl", "seed", "oracle"],
        },
        "devctx_index": {
            "motivo": "2 corrupciones: central.duckdb.CORRUPTO-1251, index.duckdb.wal.CORRUPTO-1907",
            "detectar": ["index_repo", "reindex", "devctx index", "indexar"],
        },
        "module_federation": {
            "motivo": "config asimétrica entre MFEs: merge + revert de emergencia a los 45 min",
            "detectar": ["webpack", "module federation", "module-federation", "remoteentry"],
        },
        "quarkus_live_reload": {
            "motivo": "editar Java con quarkus:dev sirviendo una medición MATA la corrida en curso "
                      "(live reload); PLAN-044 RUNBOOK §8.3 perdió 7 de 9 tandas. Invalida trabajo "
                      "YA HECHO, no lo demora",
            "detectar": ["quarkus:dev", "monolito local", "micro arriba", "medición en curso",
                         "medicion en curso", "live reload"],
        },
        "etl_legacy": {
            "motivo": "no idempotente; deja colas en ERROR con intentos=3 que no se reintentan",
            "detectar": ["etl", "legacy", "anotaciones", "registros históricos"],
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
