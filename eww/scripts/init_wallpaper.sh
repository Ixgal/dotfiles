#!/bin/bash
# Restaura el fondo de pantalla guardado al iniciar sesión.
set -u
STATE_FILE="$HOME/.config/eww/current_wallpaper"
HYPRPAPER_CONF="$HOME/.config/hypr/hyprpaper.conf"

if [ ! -f "$STATE_FILE" ]; then
    exit 0
fi

mode="${1:-}"
value="${2:-}"
if [ -z "$mode" ]; then
    IFS=':' read -r mode value < "$STATE_FILE"
fi

# Espera a que hyprland detecte todos los monitores antes de aplicar
# el fondo; si no, linux-wallpaperengine/mpvpaper solo se lanzan en
# los monitores que existían en ese momento.
wait_for_monitors() {
    local prev="" cur="" stable=0
    local i
    for i in $(seq 1 30); do
        cur="$(hyprctl monitors 2>/dev/null | awk '/^Monitor/ {print $2}')"
        if [ -n "$cur" ] && [ "$cur" = "$prev" ]; then
            stable=$((stable + 1))
            [ "$stable" -ge 2 ] && return 0
        else
            stable=0
            prev="$cur"
        fi
        sleep 1
    done
    return 0
}
wait_for_monitors

if [ "$mode" = "static" ] && [ -n "$value" ] && [ -f "$value" ]; then
    # Regenerate hyprpaper config with the saved wallpaper before hyprpaper starts
    cat > "$HYPRPAPER_CONF" <<EOF
wallpaper {
    monitor = DP-1
    path = $value
    fit_mode = cover
}
wallpaper {
    monitor = DP-2
    path = $value
    fit_mode = cover
}
EOF
fi

case "$mode" in
    static) "$HOME/.config/eww/scripts/set_wallpaper.sh" static "$value" ;;
    anim)   "$HOME/.config/eww/scripts/set_wallpaper.sh" anim "$value" ;;
    we)     "$HOME/.config/eww/scripts/set_wallpaper.sh" we "$value" ;;
esac
