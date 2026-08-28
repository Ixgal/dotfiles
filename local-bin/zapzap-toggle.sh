#!/usr/bin/env bash
# Toggle de ZapZap: enfoca si hay ventana; si no, lanza garantizando que se vea.
set -u

CLASS="com.rtosta.zapzap"
CMD="flatpak run com.rtosta.zapzap"

addr=$(hyprctl clients -j 2>/dev/null | python3 -c "
import json, sys
for w in json.load(sys.stdin):
    if w.get('class') == '$CLASS':
        print(w.get('address')); break
")

if [ -n "$addr" ]; then
    hyprctl dispatch "hl.dsp.focus({ window = 'address:$addr' })" >/dev/null 2>&1
    exit 0
fi

nohup bash -c "$CMD" >/dev/null 2>&1 &
disown 2>/dev/null || true

for i in $(seq 1 10); do
    sleep 0.5
    if hyprctl clients -j 2>/dev/null | grep -qF "\"class\": \"$CLASS\""; then
        exit 0
    fi
done

flatpak kill com.rtosta.zapzap >/dev/null 2>&1
sleep 1
nohup bash -c "$CMD" >/dev/null 2>&1 &
disown 2>/dev/null || true
