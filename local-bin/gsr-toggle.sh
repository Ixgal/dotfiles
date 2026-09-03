#!/usr/bin/env bash
OUT="$HOME/Videos"
mkdir -p "$OUT"

if ! pgrep -x gpu-screen-reco >/dev/null; then
    systemctl --user start gpu-screen-recorder.service
    notify-send -a "gpu-screen-recorder" "Grabando en segundo plano..."
    exit 0
fi

OLD=$(ls -t "$OUT"/Replay_*.mp4 2>/dev/null | head -1)
pkill -USR1 -x gpu-screen-reco
NEW=""
for _ in $(seq 1 30); do
    sleep 0.3
    NEW=$(ls -t "$OUT"/Replay_*.mp4 2>/dev/null | head -1)
    [ -n "$NEW" ] && [ "$NEW" != "$OLD" ] && break
    NEW=""
done

if [ -n "$NEW" ]; then
    FINAL="$OUT/Replay $(date +%d-%m-%Y\ %H:%M).mp4"
    i=1
    while [ -e "$FINAL" ]; do
        FINAL="$OUT/Replay $(date +%d-%m-%Y\ %H:%M)-$i.mp4"
        i=$((i + 1))
    done
    mv "$NEW" "$FINAL"
fi

notify-send -a "gpu-screen-recorder" "Clip guardado"