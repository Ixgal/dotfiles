#!/usr/bin/env bash
# Spotify en Waybar: muestra el tema actual. Se oculta si no hay reproducción.
exec 2>/dev/null

PLR=(-p spotify)

status="$(playerctl "${PLR[@]}" status)" || exit 0
[ "$status" = "Stopped" ] && exit 0

title="$(playerctl "${PLR[@]}" metadata title)"
artist="$(playerctl "${PLR[@]}" metadata artist)"
[ -z "$title" ] && exit 0

if [ "$status" = "Playing" ]; then
    icon="\uf04b"
    cls="playing"
else
    icon="\uf04c"
    cls="paused"
fi

title="${title:0:30}"
artist="${artist:0:24}"

printf '{"text":" %b %s — %s ","class":"%s","tooltip":"Spotify · %s — %s \\u00b7 %s"}' \
    "$icon" "$title" "$artist" "$cls" "$title" "$artist" "$status"