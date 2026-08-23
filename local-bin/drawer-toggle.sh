#!/usr/bin/env bash
# Lanzador de aplicaciones (nwg-drawer): abre si no está abierto, cierra si lo está.
# Se enlaza a SUPER sola (release) para que haga toggle.
set -u

if pgrep -x nwg-drawer >/dev/null 2>&1; then
    pkill -x nwg-drawer
else
    setsid nwg-drawer -is 34 -spacing 10 -c 8 -ml 220 -mr 220 -mt 130 -mb 130 >/dev/null 2>&1 &
    disown 2>/dev/null || true
fi