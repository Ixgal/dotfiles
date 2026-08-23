#!/bin/sh

opt="$(printf 'Bloquear\nSuspender\nReiniciar\nApagar\nSalir de la sesion\n' |
    wofi --dmenu --width 220 --lines 5 --prompt 'Energia')"

case "$opt" in
    Bloquear)
        if command -v hyprlock >/dev/null 2>&1; then
            hyprlock
        else
            hyprctl dispatch exit
        fi
        ;;
    Suspender)
        systemctl suspend
        ;;
    Reiniciar)
        systemctl reboot
        ;;
    Apagar)
        systemctl poweroff
        ;;
    Salir\ de\ la\ sesion)
        if command -v hyprshutdown >/dev/null 2>&1; then
            hyprshutdown
        else
            hyprctl dispatch exit
        fi
        ;;
esac