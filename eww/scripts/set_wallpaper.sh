#!/bin/bash
# Aplica un fondo de pantalla.
# Uso:
#   set_wallpaper.sh static /ruta/a/imagen.png
#   set_wallpaper.sh anim /ruta/a/video.mp4
#   set_wallpaper.sh we ID_de_workshop
set -u

STATE_FILE="$HOME/.config/eww/current_wallpaper"
MPVPAPER="$HOME/.local/bin/mpvpaper"

stop_we() {
    pkill -f "linux-wallpaperengine" >/dev/null 2>&1
}

stop_mpvpaper() {
    pkill -x mpvpaper >/dev/null 2>&1
}

apply_static() {
    local path="$1"
    stop_we
    stop_mpvpaper
    sleep 0.2
    if command -v hyprctl >/dev/null 2>&1; then
        if ! pgrep -x hyprpaper >/dev/null 2>&1; then
            hyprpaper >/dev/null 2>&1 &
        fi
        local i=0
        while [ "$i" -lt 30 ]; do
            if hyprctl hyprpaper wallpaper ",$path" >/dev/null 2>&1; then
                break
            fi
            sleep 0.2
            i=$((i+1))
        done
        hyprctl hyprpaper preload "$path" >/dev/null 2>&1
    elif command -v swaybg >/dev/null 2>&1; then
        pkill swaybg >/dev/null 2>&1
        swaybg -i "$path" -m fill >/dev/null 2>&1 &
    fi
    echo "static:$path" > "$STATE_FILE"
}

apply_anim() {
    local path="$1"
    stop_we
    pkill -x mpvpaper >/dev/null 2>&1
    sleep 0.3
    if [ ! -x "$MPVPAPER" ]; then
        echo "mpvpaper no disponible" >&2
        return 1
    fi
    nohup "$MPVPAPER" -o "loop=inf no-audio" eDP-1 "$path" >/dev/null 2>&1 &
    sleep 1
    if pgrep -x mpvpaper >/dev/null 2>&1; then
        # mpvpaper y hyprpaper no pueden coexistir: solo ahora matamos hyprpaper
        pkill -x hyprpaper >/dev/null 2>&1
        echo "anim:$path" > "$STATE_FILE"
    else
        echo "mpvpaper no arrancó; manteniendo el fondo estático" >&2
    fi
}

apply_we() {
    local id="$1"
    stop_we
    sleep 0.3
    nohup linux-wallpaperengine "$id" >/dev/null 2>&1 &
    sleep 1
    if pgrep -f linux-wallpaperengine >/dev/null 2>&1; then
        pkill -x hyprpaper >/dev/null 2>&1
        echo "we:$id" > "$STATE_FILE"
    else
        echo "linux-wallpaperengine no arrancó; manteniendo el fondo estático" >&2
    fi
}

case "${1:-}" in
    static) apply_static "${2:-}" ;;
    anim)   apply_anim "${2:-}" ;;
    we)     apply_we "${2:-}" ;;
    *)
        echo "uso: set_wallpaper.sh {static PATH | anim PATH | we ID}" >&2
        exit 1
        ;;
esac