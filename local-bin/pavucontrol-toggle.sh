#!/usr/bin/env bash
if pgrep -x pavucontrol-qt >/dev/null; then
    hyprctl dispatch focuswindow "class:pavucontrol-qt"
else
    pavucontrol-qt &
fi