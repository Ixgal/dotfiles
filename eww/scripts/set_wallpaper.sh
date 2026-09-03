#!/bin/bash
# Aplica un fondo de pantalla con un clic.
# Uso: set_wallpaper.sh static /ruta/a/imagen.png
set -u

STATE_FILE="$HOME/.config/eww/current_wallpaper"
HYPRPAPER_CONF="$HOME/.config/hypr/hyprpaper.conf"
WALLPAPER_DIR="$HOME/Pictures/Wallpapers"

write_hyprpaper_conf() {
    local path="$1"
    cat > "$HYPRPAPER_CONF" <<EOF
wallpaper {
    monitor = DP-1
    path = $path
    fit_mode = cover
}
wallpaper {
    monitor = DP-2
    path = $path
    fit_mode = cover
}
EOF
}

restart_hyprpaper() {
    pkill hyprpaper 2>/dev/null
    sleep 0.5
    hyprpaper >/dev/null 2>&1 &
    disown
    sleep 2
}

apply_static() {
    local path="$1"
    # Kill any other wallpaper renderers
    pkill -f "[l]inux-wallpaperengine" 2>/dev/null
    pkill -x mpvpaper 2>/dev/null

    # Write hyprpaper config and restart
    write_hyprpaper_conf "$path"
    restart_hyprpaper

    # Save state
    echo "static:$path" > "$STATE_FILE"

    # Visual feedback
    timeout 3 notify-send -i image -t 2000 "Fondo de pantalla" "$(basename "$path")" 2>/dev/null
}

apply_anim() {
    local path="$1"
    pkill -f "[l]inux-wallpaperengine" 2>/dev/null
    pkill -x hyprpaper 2>/dev/null
    sleep 0.3
    nohup mpvpaper -o "loop=inf no-audio" -f "$path" >/dev/null 2>&1 &
    sleep 1
    echo "anim:$path" > "$STATE_FILE"
    timeout 3 notify-send -i image -t 2000 "Fondo animado" "$(basename "$path")" 2>/dev/null
}

get_monitors() {
    hyprctl monitors 2>/dev/null | awk '/^Monitor/ {print $2}'
}

apply_we() {
    local path="$1"
    local prev_mode="" prev_path=""
    local -a args=()
    local mon
    while IFS= read -r mon; do
        [ -n "$mon" ] && args+=(--screen-root "$mon")
    done < <(get_monitors)
    if [ -f "$STATE_FILE" ]; then
        IFS=':' read -r prev_mode prev_path < "$STATE_FILE" || true
    fi
    pkill -f "[l]inux-wallpaperengine" 2>/dev/null
    pkill -x hyprpaper 2>/dev/null
    pkill -x mpvpaper 2>/dev/null
    sleep 0.3
    # setsid desacopla el proceso del grupo del lanzador (EWW/submap),
    # evitando que muera cuando el script que lo invoco termina.
    setsid linux-wallpaperengine --silent --fps 30 "${args[@]}" "$path" \
        >"$HOME/.cache/wallpaper-engine.log" 2>&1 &
    local pid=$!
    disown
    sleep 5
    if kill -0 "$pid" 2>/dev/null; then
        echo "we:$path" > "$STATE_FILE"
        timeout 3 notify-send -i image -t 2000 "Fondo Wallpaper Engine" "$(basename "$path")" 2>/dev/null
    else
        timeout 3 notify-send -i dialog-error -t 3000 "Wallpaper Engine" "No se pudo iniciar: $(basename "$path")" 2>/dev/null
        if [ -n "$prev_mode" ] && [ -n "$prev_path" ]; then
            "$0" "$prev_mode" "$prev_path"
        fi
    fi
}

case "${1:-}" in
    static) apply_static "${2:-}" ;;
    anim)   apply_anim "${2:-}" ;;
    we)     apply_we "${2:-}" ;;
    *)      echo "uso: set_wallpaper.sh {static PATH | anim PATH | we PATH}" >&2; exit 1 ;;
esac
