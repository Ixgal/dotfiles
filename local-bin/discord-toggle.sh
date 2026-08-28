#!/bin/sh

case "${1:-mute}" in
  mute)   combo="ctrl+shift+m" ;;
  deafen) combo="ctrl+shift+d" ;;
  *) exit 1 ;;
esac

hyprctl clients -j | grep -q '"class": "discord"' || exit 0

prev=$(hyprctl activewindow -j | sed -n 's/.*"address": "\([^"]*\)".*/\1/p')

hyprctl dispatch focuswindow "class:discord" >/dev/null 2>&1
sleep 0.1
xdotool key "$combo"
[ -n "$prev" ] && hyprctl dispatch focuswindow "address:$prev" >/dev/null 2>&1
