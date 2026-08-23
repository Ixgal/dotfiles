#!/usr/bin/env bash
set -euo pipefail

IFACE="wlan0"
MODE=""
for arg in "$@"; do
    case "$arg" in
        --status) MODE="--status" ;;
        *) IFACE="$arg" ;;
    esac
done

STYLE="$HOME/.config/waybar/wifi-menu.css"
POPUP_W=330

get_screen() {
    hyprctl monitors -j 2>/dev/null | python3 -c '
import json, sys
try:
    ms = json.load(sys.stdin)
    for m in ms:
        if m.get("focused"):
            w, h, s = m["width"], m["height"], m.get("scale") or 1
            break
    else:
        w, h, s = ms[0]["width"], ms[0]["height"], ms[0].get("scale") or 1
    # Hyprland reporta ancho físico; wofi posiciona en coords lógicas.
    print(int(w / s), int(h / s))
except Exception:
    print("1280 720")
'
}

launch_wofi() {
    local lines="$1" prompt="$2"; shift 2
    local cxy sw sh cx cy x maxx
    read -r cx cy <<< "$(hyprctl cursorpos 2>/dev/null | tr -d ' ' | tr ',' ' ')"
    [ -z "$cx" ] && { cx=1240; cy=40; }
    read -r sw sh <<< "$(get_screen)"
    x=$(( cx - POPUP_W / 2 ))
    [ "$x" -lt 8 ] && x=8
    maxx=$(( sw - POPUP_W - 8 ))
    [ "$x" -gt "$maxx" ] && x=$maxx

    wofi --dmenu --width "$POPUP_W" --lines "$lines" --style "$STYLE" \
        --location top_left --xoffset "$x" --yoffset 4 --prompt "$prompt" "$@"
}

is_connected() {
    iwctl station "$IFACE" show 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | grep -q "State.*connected"
}

current_net() {
    iwctl station "$IFACE" show 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | awk '{for(i=1;i<NF;i++) if($i=="network") print $(i+1)}'
}

signal_bars() {
    case "$1" in
        4) printf "▂▅▆█" ;;
        3) printf "▂▅▆" ;;
        2) printf "▂▅" ;;
        1) printf "▂" ;;
        *) printf " " ;;
    esac
}

list_networks() {
    local out
    out="$(timeout 8 iwctl station "$IFACE" get-networks 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')"
    printf '%s\n' "$out" | awk '
        {
            if (match($0, /(psk|open|wpa[0-9]*|sae)[[:space:]]+[*]+/)) {
                name = substr($0, 1, RSTART - 1)
                gsub(/^[[:space:]>]+|[[:space:]]+$/, "", name)
                if (name == "") next
                sec = substr($0, RSTART, RLENGTH)
                gsub(/[[:space:]]+/, " ", sec)
                split(sec, a, " ")
                n = gsub(/\*/, "")
                printf "%s\t%s\t%d\n", name, a[1], n
            }
        }' | sort -t $'\t' -k3 -rn
}

refresh_scan() {
    notify-send -i network-wireless "WiFi" "Buscando redes..."
    iwctl station "$IFACE" scan > /dev/null 2>&1 || true
    sleep 2
}

is_known() {
    iwctl known-networks list 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' | awk -v tgt="$1" '
        match($0, /(psk|open|wpa[0-9]*|sae)[[:space:]]/) {
            n = substr($0, 1, RSTART - 1)
            gsub(/[[:space:]]/, "", n)
            if (n == tgt) found = 1
        }
        END { exit !found }'
}

try_connect() {
    local name="$1" sec="$2" pass="" err=""
    if is_connected && [ "$(current_net)" = "$name" ]; then
        notify-send -i network-wireless "WiFi" "Ya estás conectado a $name"
        return
    fi

    if [ "$sec" = "open" ]; then
        err="$(iwctl station "$IFACE" connect "$name" 2>&1 | sed 's/\x1b\[[0-9;]*m//g')" || true
    elif is_known "$name"; then
        err="$(iwctl station "$IFACE" connect "$name" 2>&1 | sed 's/\x1b\[[0-9;]*m//g')" || true
    else
        pass="$(launch_wofi 1 "Contraseña de $name" --password 2>/dev/null)" || true
        if [ -z "$pass" ]; then
            notify-send -i network-wireless "WiFi" "Conexión a $name cancelada"
            return
        fi
        err="$(iwctl station "$IFACE" connect "$name" --passphrase "$pass" 2>&1 | sed 's/\x1b\[[0-9;]*m//g')" || true
    fi

    sleep 2
    if is_connected && [ "$(current_net)" = "$name" ]; then
        notify-send -i network-wireless "WiFi" "Conectado a $name"
    else
        notify-send -u critical -i network-wireless "WiFi" "No se pudo conectar a $name"
    fi
}

menu_networks() {
    refresh_scan
    local lines cur opt name sec n choice
    lines="$(list_networks)"
    if [ -z "$lines" ]; then
        notify-send -i network-wireless "WiFi" "No se encontraron redes disponibles"
        return
    fi
    cur="$(current_net)"

    opt=""
    while IFS=$'\t' read -r name sec n; do
        [ -z "$name" ] && continue
        if [ "$name" = "$cur" ]; then
            opt+="$(printf '● %s\t%s\t%s\n' "$name" "$sec" "$(signal_bars "$n")")\n"
        else
            opt+="$(printf '   %s\t%s\t%s\n' "$name" "$sec" "$(signal_bars "$n")")\n"
        fi
    done <<< "$lines"
    opt+="\u23ce Salir"

    choice="$(printf '%b' "$opt" | launch_wofi 8 " WiFi disponible" 2>/dev/null)" || true
    [ -z "$choice" ] && return
    [ "$choice" = "⏎ Salir" ] && return

    name="$(printf '%s' "$choice" | cut -f1 | sed 's/^ *//;s/^● *//')"
    sec="$(printf '%s' "$choice" | cut -f2)"
    [ -z "$name" ] && return
    try_connect "$name" "$sec"
}

menu_main() {
    if is_connected; then
        local cur opt choice
        cur="$(current_net)"
        opt="\uf0e7  Desconectar de $cur"
        opt+="\n\uf1e0  Otras redes disponibles..."
        opt+="\n\ueaaa  Salir"

        choice="$(printf '%b' "$opt" | launch_wofi 3 " WiFi ($cur)" 2>/dev/null)" || true
        case "$choice" in
            *"Desconectar"*)
                notify-send -i network-wireless "WiFi" "Desconectando de $cur..."
                iwctl station "$IFACE" disconnect > /dev/null 2>&1 || true
                sleep 2
                menu_networks
                ;;
            *"Otras redes"*) menu_networks ;;
            *) return ;;
        esac
    else
        menu_networks
    fi
}

case "$MODE" in
    --status) is_connected && echo "connected" || echo "disconnected" ;;
    *) menu_main ;;
esac
