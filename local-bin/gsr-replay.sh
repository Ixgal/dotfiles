#!/usr/bin/env bash
export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-$(basename /run/user/$(id -u)/wayland-* 2>/dev/null | head -1)}"
export HYPRLAND_INSTANCE_SIGNATURE="${HYPRLAND_INSTANCE_SIGNATURE:-$(ls /tmp/hypr 2>/dev/null | head -1)}"

OUT="$HOME/Videos"
mkdir -p "$OUT"

MAIN=$(hyprctl monitors -j | python3 -c "import json,sys; print(next(m['name'] for m in json.load(sys.stdin) if m.get('focused')))")
DEVICES=$(gpu-screen-recorder --list-audio-devices)
MIC=$(echo "$DEVICES" | grep -i "fifine" | grep -i "input" | head -1 | cut -d'|' -f1)
if [ -z "$MIC" ]; then
    MIC=$(echo "$DEVICES" | grep -i "hyperx" | grep -i "input" | head -1 | cut -d'|' -f1)
fi
if [ -z "$MIC" ]; then
    MIC="default_input"
fi

exec gpu-screen-recorder -v no -w "$MAIN" -c mp4 -a "default_output|$MIC" -f 60 -r 180 -o "$OUT"