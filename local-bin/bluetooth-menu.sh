#!/usr/bin/env bash
# Menú de Bluetooth para waybar.
# - Opciones: encender/apagar, conectar/desconectar emparejados, escanear nuevos.
# - Usa wofi como selector y bluetoothctl.

set -euo pipefail

ICON_ON="on:\uf293   off:\uf294"
BT="bluetoothctl"

bt_on() { "$BT" show | grep -q "Powered: yes"; }

toggle_power() {
    if bt_on; then
        "$BT" power off > /dev/null
        notify-send -i bluetooth "Bluetooth" "Apagado"
    else
        "$BT" power on > /dev/null
        notify-send -i bluetooth "Bluetooth" "Encendido"
    fi
}

show_status() {
    local powered
    if bt_on; then
        powered="\uf293  Bluetooth encendido"
    else
        powered="\uf294  Bluetooth apagado"
    fi
    echo -e "$powered"
    echo -e "\uf204  Conectado / vinculado:"
    while read -r mac alias; do
        if "$BT" info "$mac" | grep -q "Connected: yes"; then
            echo -e "    \uf0e7  $alias  ($mac)  [conectado]"
        fi
    done < <("$BT" devices | awk '{print $2, $3}')
}

menu_main() {
    local opts
    if bt_on; then
        opts="\uf293  Apagar Bluetooth"
    else
        opts="\uf294  Encender Bluetooth"
    fi
    opts+="\n\uf1e6  Dispositivos vinculados\n\uf076  Buscar dispositivos nuevos\n\ueaaa  Salir"

    choice=$(printf "%b" "$opts" | wofi --show dmenu --prompt " Bluetooth" 2>/dev/null) || true
    case "$choice" in
        *"Apagar"*) toggle_power ;;
        *"Encender"*) toggle_power ;;
        *"vinculados"*) menu_paired ;;
        *"nuevos"*) menu_scan ;;
        *) return ;;
    esac
}

menu_paired() {
    if ! bt_on; then
        notify-send -u critical -i bluetooth "Bluetooth" "Bluetooth apagado. Enciéndelo primero."
        return
    fi
    "$BT" agent on > /dev/null 2>&1 || true
    local devs
    devs=$("$BT" devices | awk '{print $3"  ["$2"]"}')
    if [ -z "$devs" ]; then
        notify-send -i bluetooth "Bluetooth" "No hay dispositivos vinculados.\nBusca dispositivos nuevos."
        return
    fi
    choice=$(printf "%s\n%s" "$devs" "⤺  Volver" | wofi --show dmenu --prompt " Bluetooth vinculado" 2>/dev/null) || true
    [ -z "$choice" ] && return
    [ "$choice" = "⤺  Volver" ] && { menu_main; return; }

    mac=$(echo "$choice" | grep -oP '(?<=\[)[0-9A-F:]{17}(?=\])' || true)
    [ -z "$mac" ] && { menu_paired; return; }
    if "$BT" info "$mac" | grep -q "Connected: yes"; then
        "$BT" disconnect "$mac" > /dev/null
        notify-send -i bluetooth "Bluetooth" "Desconectado: $(echo "$choice" | awk '{print $1}')"
    else
        "$BT" connect "$mac" > /dev/null
        notify-send -i bluetooth "Bluetooth" "Conectando: $(echo "$choice" | awk '{print $1}')"
    fi
    menu_paired
}

do_pair() {
    local mac alias
    mac="$1"
    alias="$2"
    notify-send -i bluetooth "Bluetooth" "Vinculando $alias..."
    "$BT" pair "$mac" > /dev/null
    "$BT" trust "$mac" > /dev/null
    "$BT" connect "$mac" > /dev/null
    notify-send -i bluetooth "Bluetooth" "$alias vinculado y conectado"
}

menu_scan() {
    if ! bt_on; then
        notify-send -u critical -i bluetooth "Bluetooth" "Bluetooth apagado. Enciéndelo primero."
        return
    fi
    # Registra agente de confirmacion automatica para que el emparejamiento
    # (pair) no falle pidiendo un PIN interactivo que nadie legitima.
    "$BT" agent on > /dev/null 2>&1 || true
    notify-send -i bluetooth "Bluetooth" "Escaneando dispositivos..."
    "$BT" scan on > /dev/null 2>&1 &
    sleep 6
    "$BT" scan off > /dev/null 2>&1 || true
    local devs
    devs=$("$BT" devices | awk '{print $3"  ["$2"]"}')
    if [ -z "$devs" ]; then
        notify-send -i bluetooth "Bluetooth" "No se encontraron dispositivos nuevos."
        return
    fi
    choice=$(printf "%s\n%s" "$devs" "⤺  Volver" | wofi --show dmenu --prompt " Bluetooth nuevo" 2>/dev/null) || true
    [ -z "$choice" ] && return
    [ "$choice" = "⤺  Volver" ] && { menu_main; return; }
    mac=$(echo "$choice" | grep -oP '(?<=\[)[0-9A-F:]{17}(?=\])' || true)
    [ -z "$mac" ] && { menu_scan; return; }
    do_pair "$mac" "$(echo "$choice" | awk '{print $1}')"
    menu_main
}

case "${1:-}" in
    --status) show_status ;;
    *) menu_main ;;
esac