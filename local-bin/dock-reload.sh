#!/usr/bin/env bash
# Recarga el dock (waybar inferior) tras editar dock.jsonc / dock.css.
# Uso:
#   dock-reload.sh          -> recarga config + CSS (señal SIGUSR2 a waybar)
#   dock-reload.sh --restart-> reinicia por completo solo el dock (kill + relanzar)
# El dock se lanza a mano con:  waybar -c .../dock.jsonc -s .../dock.css
set -u

CFG="$HOME/.config/waybar/dock.jsonc"
CSS="$HOME/.config/waybar/dock.css"

if [ "${1:-}" = "--restart" ]; then
    # Matar SOLO el dock (el "[w]" evita que pkill se case con esta línea de comando)
    pkill -f '[w]aybar.*dock.jsonc' 2>/dev/null
    sleep 0.5
    nohup waybar -c "$CFG" -s "$CSS" >/tmp/dock-run.log 2>&1 &
    disown
    echo "Dock reiniciado."
else
    if ! pgrep -x waybar >/dev/null 2>&1; then
        echo "waybar no está en ejecución; lanzando el dock..."
        nohup waybar -c "$CFG" -s "$CSS" >/tmp/dock-run.log 2>&1 &
        disown
        exit 0
    fi
    pkill -USR2 -x waybar
    echo "Config + CSS recargados (SIGUSR2)."
fi