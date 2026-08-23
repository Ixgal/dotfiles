#!/bin/bash
# Abre/cierra el menú de fondos (SUPER+W).
# Al abrirlo regenera eww.yuck con la lista actual de fondos y recarga.
set -u

LOG="/tmp/opencode/eww_toggle.log"
echo "$(date +%H:%M:%S) toggle iniciado" >> "$LOG"

if ! pgrep -x eww > /dev/null 2>&1; then
    echo "$(date +%H:%M:%S) daemon no existe, arrancando" >> "$LOG"
    eww daemon > /dev/null 2>&1 &
    for _ in $(seq 1 20); do
        pgrep -x eww > /dev/null 2>&1 && break
        sleep 0.1
    done
fi

if eww active-windows 2>/dev/null | grep -q "wallpaper-menu"; then
    echo "$(date +%H:%M:%S) menú abierto, cerrándolo" >> "$LOG"
    eww close wallpaper-menu >/dev/null 2>&1
    exit 0
fi

echo "$(date +%H:%M:%S) regenerando lista" >> "$LOG"
python3 /home/jairo/.config/eww/scripts/list_wallpapers.py >> "$LOG" 2>&1

echo "$(date +%H:%M:%S) reload" >> "$LOG"
eww reload >> "$LOG" 2>&1
sleep 0.3

echo "$(date +%H:%M:%S) abriendo menú" >> "$LOG"
eww open wallpaper-menu >> "$LOG" 2>&1

if eww active-windows 2>/dev/null | grep -q "wallpaper-menu"; then
    echo "$(date +%H:%M:%S) menú abierto OK" >> "$LOG"
else
    echo "$(date +%H:%M:%S) ERROR: el menú no se abrió" >> "$LOG"
    notify-send -i image "Fondos" "No se pudo abrir el menú de fondos" 2>/dev/null
fi
