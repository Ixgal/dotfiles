#!/usr/bin/env bash
# Helper del dock: si la app ya está abierta la enfoca; si no, la lanza.
# Uso:  launcher-toggle.sh "clase1 clase2 ..." "comando..."
#  - clases: posibles nombres de clase de ventana (Wayland/XWayland) para detectar la app abierta.
#  - comando: lo que se ejecuta si no está abierta.
set -u

classes="$1"
shift
cmd="$*"

found=""
for c in $classes; do
    if hyprctl clients -j 2>/dev/null | grep -qF "\"class\": \"$c\""; then
        found="$c"
        break
    fi
done

if [ -n "$found" ]; then
    addr=$(hyprctl clients -j 2>/dev/null | python3 -c "
import json, sys
cls = '$found'
for w in json.load(sys.stdin):
    if w.get('class') == cls:
        print(w.get('address')); break
")
    if [ -n "$addr" ]; then
        hyprctl dispatch "hl.dsp.focus({ window = 'address:$addr' })" >/dev/null 2>&1
    fi
    exit 0
fi

nohup bash -c "$cmd" >/dev/null 2>&1 &
disown 2>/dev/null || true