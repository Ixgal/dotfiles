#!/usr/bin/env bash
# Menú desplegable de Spotify: control de reproducción y volumen.
set -u
exec 2>/dev/null

PLR=(-p spotify)
STYLE="$HOME/.config/waybar/spotify-menu.css"
POPUP_W=380

status="$(playerctl "${PLR[@]}" status 2>/dev/null || echo Stopped)"
[ "$status" = "Stopped" ] && running=false || running=true

title="$(playerctl "${PLR[@]}" metadata title 2>/dev/null)"
artist="$(playerctl "${PLR[@]}" metadata artist 2>/dev/null)"
album="$(playerctl "${PLR[@]}" metadata album 2>/dev/null)"

launch_wofi() {
    local lines="$1" prompt="$2"; shift 2

    # Ancla el menú justo debajo del módulo de Spotify (barra derecha,
    # a la izquierda del botón de apagado).
    local sw sh
    read -r sw sh <<< "$(hyprctl monitors -j 2>/dev/null | python3 -c '
import json, sys
try:
    ms = json.load(sys.stdin)
    for m in ms:
        if m.get("focused"):
            w, h, s = m["width"], m["height"], m.get("scale") or 1
            break
    else:
        w, h, s = ms[0]["width"], ms[0]["height"], ms[0].get("scale") or 1
    print(int(w / s), int(h / s))
except Exception:
    print("1280 720")
')"

    wofi --dmenu --width "$POPUP_W" --lines "$lines" --style "$STYLE" \
        --location top_right --xoffset -50 --yoffset 44 --prompt "$prompt" \
        --hide-search --hide-scroll "$@"
}

vol="$(playerctl "${PLR[@]}" volume 2>/dev/null)"
[ -z "$vol" ] && vol=0
volt=$(( $(awk "BEGIN{printf \"%.0f\", $vol*100}") ))
volchar="\uf028"
[ "$volt" -eq 0 ] && volchar="\uf6a9"

if $running; then
    if [ "$status" = "Playing" ]; then
        play_opt="\uf04c  Pausar"
    else
        play_opt="\uf04b  Reproducir"
    fi
    track="\uf001  $title"
    [ -n "$artist" ] && track="$track\n        $artist"
else
    track="\uf001  Sin reproducción"
    play_opt="\uf04b  Reproducir"
fi

opt="$track\n"
opt+="$play_opt\n"
opt+="\uf04e  Siguiente\n"
opt+="\uf04a  Anterior\n"
opt+="$volchar  Volumen: ${volt}%\n"
opt+="\uf0de  Subir volumen (+10%)\n"
opt+="\uf0dd  Bajar volumen (-10%)\n"
opt+="\uf07a  Abrir Spotify"

lines=9
choice="$(printf '%b' "$opt" | launch_wofi "$lines" " Spotify" 2>/dev/null)" || true
[ -z "$choice" ] && exit 0

case "$choice" in
    *"Pausar"*)          playerctl "${PLR[@]}" pause ;;
    *"Reproducir"*)      playerctl "${PLR[@]}" play ;;
    *"Siguiente"*)       playerctl "${PLR[@]}" next ;;
    *"Anterior"*)        playerctl "${PLR[@]}" previous ;;
    *"Subir volumen"*)   playerctl "${PLR[@]}" volume 0.1+ ;;
    *"Bajar volumen"*)   playerctl "${PLR[@]}" volume 0.1- ;;
    *"Abrir Spotify"*)   flatpak run com.spotify.Client >/dev/null 2>&1 &
        ;;
esac