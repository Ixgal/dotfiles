#!/usr/bin/env bash
# Si ya hay una ventana de opencode, la enfoca; si no, la abre.
addr=$(hyprctl clients -j 2>/dev/null | python3 -c "
import json, sys
for w in json.load(sys.stdin):
    if w.get('class') == 'opencode' or 'opencode' in (w.get('title') or '').lower():
        print(w.get('address')); break
")
if [ -n "$addr" ]; then
    hyprctl dispatch "hl.dsp.focus({ window = 'address:$addr' })" >/dev/null 2>&1
else
    cd "$HOME" || exit 1
    kitty --class opencode --title opencode opencode
fi