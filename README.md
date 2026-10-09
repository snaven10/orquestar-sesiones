# orquestar-sesiones

Skill de Claude Code para levantar sesiones Claude especializadas en paralelo, en tu máquina
o en otra por SSH. Propone qué agentes hacen falta, **pide aval antes de gastar** y cosecha lo
que aprendió cada sesión. El trabajo mecánico lo hace `assets/orq.py` (un solo archivo, solo
stdlib); `SKILL.md` es el contrato de cómo usarlo.

## Requisitos

- [Claude Code](https://code.claude.com) instalado y con sesión iniciada
- Python >= 3.11 (usa `tomllib` de la stdlib; sin dependencias externas)
- git

## Instalación

```bash
git clone <url-de-este-repo> ~/.claude/skills/orquestar-sesiones

# comando `orq` (wrapper mínimo; ~/.local/bin debe estar en el PATH)
mkdir -p ~/.local/bin
cat > ~/.local/bin/orq <<'WRAP'
#!/bin/sh
exec python3 "$HOME/.claude/skills/orquestar-sesiones/assets/orq.py" "$@"
WRAP
chmod +x ~/.local/bin/orq

# tu configuración (opcional: sin ella orq corre en la máquina local)
mkdir -p ~/.orq
cp ~/.claude/skills/orquestar-sesiones/assets/config.example.toml ~/.orq/config.toml
```

Editá `~/.orq/config.toml`: máquinas, workspaces, specialists y recursos exclusivos están
comentados en el ejemplo. Se aplica encima de los defaults genéricos de `assets/roles.py`.

## Primer uso

```bash
cd ~/ruta/a/un/repo
orq need "lo que querés trabajar"     # propone sesiones, agentes, costo y un token T-xxxxxx
orq spawn --token T-xxxxxx            # solo después de revisar la propuesta y dar el aval
orq status                            # estado de las sesiones
```

`spawn` sin un token de un `need` previo no existe: es la garantía de que nadie gasta sin ver
antes la propuesta. Al terminar, `orq harvest` recoge los aprendizajes de las sesiones.

## Contenido

- `SKILL.md` — contrato para el orquestador (flujo, reglas, trampas verificadas)
- `assets/orq.py` — el script; `assets/roles.py` — política genérica; `assets/config.example.toml`
- `references/escenarios.md` — los escenarios de fallo y su mitigación
- `plans/` — historia de diseño del proyecto. Los SHAs que citan son anteriores a la publicación
  (el historial se reescribió) y ya no existen en este repo.

## Licencia

MIT. Ver [LICENSE](LICENSE).
