#!/usr/bin/env bash
# Captura de pantalla -> portapapeles (+ copia en ~/Pictures/Screenshots)
# Uso: screenshot.sh [region|screen|window]
set -euo pipefail

MODE="${1:-region}"
DIR="$HOME/Pictures/Screenshots"
mkdir -p "$DIR"
FILE="$DIR/$(date +%Y-%m-%d_%H-%M-%S).png"

case "$MODE" in
  region)
    GEOM="$(slurp -d)" || exit 0   # ESC cancela
    grim -g "$GEOM" "$FILE"
    ;;
  window)
    GEOM="$(hyprctl activewindow | awk '/^\tat:/{split($2,a,","); x=a[1]; y=a[2]} /^\tsize:/{split($2,b,","); print x","y" "b[1]"x"b[2]}')"
    grim -g "$GEOM" "$FILE"
    ;;
  screen|*)
    grim "$FILE"
    ;;
esac

wl-copy --type image/png < "$FILE"
command -v notify-send >/dev/null && notify-send -i "$FILE" "Captura copiada" "$(basename "$FILE")" || true
