#!/bin/bash
# Restaura el fondo de pantalla guardado al iniciar sesión.
set -u
STATE_FILE="$HOME/.config/eww/current_wallpaper"

if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

mode="${1:-}"
value="${2:-}"
if [ -z "$mode" ]; then
    IFS=':' read -r mode value < "$STATE_FILE"
fi

case "$mode" in
    static) "$HOME/.config/eww/scripts/set_wallpaper.sh" static "$value" ;;
    anim)   "$HOME/.config/eww/scripts/set_wallpaper.sh" anim "$value" ;;
    we)     "$HOME/.config/eww/scripts/set_wallpaper.sh" we "$value" ;;
esac