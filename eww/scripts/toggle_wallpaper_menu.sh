#!/bin/bash
# Toggle wallpaper picker menu (SUPER+X / SUPER+Q).
# El menu se controla con el teclado mediante un submap de Hyprland
# (flechas + Enter): al abrir se entra en el submap y al cerrar se sale.
set -u

EWW_DIR="$HOME/.config/eww"
SCRIPTS="$EWW_DIR/scripts"

submap_enter() { hyprctl dispatch "hl.dsp.submap('wallpapermenu')" >/dev/null 2>&1; }
submap_reset() { hyprctl dispatch "hl.dsp.submap('reset')" >/dev/null 2>&1; }

# Start eww daemon if not running
if ! pgrep -x eww > /dev/null 2>&1; then
    eww daemon > /dev/null 2>&1 &
    for _ in $(seq 1 20); do
        pgrep -x eww > /dev/null 2>&1 && break
        sleep 0.1
    done
fi

# If menu is open, close it and leave the submap
if eww active-windows 2>/dev/null | grep -q "wallpaper-menu"; then
    eww close wallpaper-menu >/dev/null 2>&1
    submap_reset
    exit 0
fi

# Regenerate the yuck file with current wallpapers
python3 "$SCRIPTS/list_wallpapers.py" >/dev/null 2>&1

# Reload eww to pick up changes
eww reload >/dev/null 2>&1
sleep 0.3

# Cursor starts on the current wallpaper
cur_path=""
if [ -f "$EWW_DIR/current_wallpaper" ]; then
    raw=$(cat "$EWW_DIR/current_wallpaper" 2>/dev/null | tr -d '\n')
    case "$raw" in
        *:*) cur_path="${raw#*:}" ;;
    esac
fi
eww update "wm_sel=$cur_path" >/dev/null 2>&1
python3 "$SCRIPTS/wallpaper_menu_nav.py" sync >/dev/null 2>&1

# Open the menu
eww open wallpaper-menu >/dev/null 2>&1

submap_enter
