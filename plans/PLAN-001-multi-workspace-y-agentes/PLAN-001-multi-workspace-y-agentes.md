# PLAN-001 — orq: workspaces fuera de MI-EMPRESA + propuesta real de agentes faltantes

**Fecha:** 2026-10-08
**Fase:** 2 (Ejecución) — aprobado por el usuario 2026-10-08 (3 escalones + scout, scope siempre preguntado)
**Diseño:** [`PLAN-001-design.md`](./PLAN-001-design.md)
**Proyectos:** orquestar-sesiones (`~/.claude/skills/orquestar-sesiones`) — **no es repo git**
**Origen:** el usuario quiere despachar el PLAN-001 de `~/personal/claude-dashboard` con `orq`; la investigación mostró que la propuesta de agentes nunca se implementó

## 1. Qué resuelve
`orq` solo sabe trabajar en `~/mi-empresa` y, cuando falta un specialist, imprime un recordatorio y
levanta la sesión **sin agente y sin avisar**. La intención original (sesión `5d7c5e7d`, 21–22/09)
era otra: *"si no se tiene el agente… sugiere como deberían quedar estructurados los agentes y
preguntar si los quiere guardar en el proyecto o mono repo o global"*. Este plan cierra esa brecha
y habilita repos sueltos como `~/personal/claude-dashboard`.

## 2. Hallazgos que reorientan el plan (verificados 2026-10-08)
- **No hubo plan formal de orq.** El diseño solo existe en la conversación `5d7c5e7d` y en SKILL.md.
- **La propuesta de agentes es 100 % prosa** (SKILL.md §3). En código: `resolver_specialist`
  (orq.py:190) detecta, orq.py:322-336 imprime, y **nada escribe un agente nunca** — `AGENTS_DIR`
  solo se lee con `glob` (orq.py:364, :1029).
- **Spawn silencioso**: orq.py:641 `if p["specialist"]:` → sin specialist corre una sesión genérica.
  En `~/.orq/tokens/` hay propuestas con 2, 5 y 6 sesiones sin specialist (T-aa3b81, T-2ab97d,
  T-d86219). Se taparon editando `roles.py` a mano (ver `roles.py.bak-20261008-093640`).
- **No existe "skill para proponer agentes".** `claude-automation-recommender` es read-only,
  genérica por stack, no resuelve el scope ni escribe nada. `agent-evolve` solo agrega
  `## Learned Patterns` a agentes existentes. `skill-creator` crea skills, no agentes.
- **`~/mi-empresa` hardcodeado** en roles.py:10/:22 y orq.py:142, 260, 365, 436, 458, 495, 638/640,
  819-820 (`PLANS`, `AGENTS_DIR`); `RUIDO` (orq.py:164) es vocabulario MI-EMPRESA.
- **orq.py no puede llamar MCPs** (devctx, context7): es Python plano. La parte "inteligente" de la
  propuesta la tiene que hacer la sesión Claude que usa la skill → DD-3.

## 3. Tasks y orden
| Task | Qué | Especialista | Depende de | Estado |
|------|-----|--------------|------------|--------|
| TASK-000 | Snapshot git de la skill + captura "antes" de salidas MI-EMPRESA | directo (orquestador) | — | `done` |
| TASK-001 | Workspaces declarativos: `multi` (~/mi-empresa) y `repo` (suelto) | general-purpose (sonnet) | TASK-000 | `done` |
| TASK-002 | Escalones 1-2: overlay, verificación de existencia, match por afinidad, `agent use` | general-purpose (sonnet) | TASK-001 | `pending` |
| TASK-003 | Escalón 3: arquetipo `scout` + `orq scout` con token | general-purpose (sonnet) | TASK-002 | `pending` |
| TASK-004 | Gate en spawn: sin specialist → rc=2 salvo `--sin-specialist` | general-purpose (sonnet) | TASK-002 | `pending` |
| TASK-007 | `orq agent save --scope` (scope obligatorio, sin default) | general-purpose (sonnet) | TASK-002 | `pending` |
| TASK-005 | SKILL.md §3 reescrito (3 escalones) + escenario 17 | general-purpose (sonnet) | TASK-003, TASK-004, TASK-007 | `pending` |
| TASK-006 | Verificación: no-regresión MI-EMPRESA + dry-run claude-dashboard (incluye 1 scout real, con aval) | general-purpose (sonnet) | TASK-005 | `pending` |

**Olas:** ① 000 → ② 001 → ③ 002 → ④ 003, 004, 007 **en serie** (los tres tocan `main()` y
`cmd_spawn`/`cmd_need` de orq.py: paralelo = conflictos) → ⑤ 005 → ⑥ 006.
Todas con sub-agentes en esta sesión: `orq` es justamente lo que se está arreglando.

## 4. Fuera de alcance
- Sincronizar agentes local↔remota (pendiente desde el 22/09, no se toca).
- Crear los specialists faltantes de MI-EMPRESA (plantillas, tickets, qa, validator): con este plan
  se pueden proponer por el flujo nuevo, pero crearlos es trabajo aparte.
- Una skill `proponer-agente` independiente de orq, y una capa automática de agentes globales (DD-7).
- Despachar el PLAN-001 del dashboard: arranca cuando este plan cierre.

## 5. Cierre
<!-- SE LLENA AL CERRAR EL PLAN -->
