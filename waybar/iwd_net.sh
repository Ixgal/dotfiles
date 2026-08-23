#!/bin/sh
IFACE="${1:-wlan0}"

out="$(timeout 3 iwctl station "$IFACE" show 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g')"

state="$(printf '%s\n' "$out" | awk '{for(i=1;i<NF;i++) if($i=="State") print $(i+1)}')"
NOTIFY="${2:-}"

if [ "$state" != "connected" ]; then
    if [ "$NOTIFY" = "--notify" ]; then
        notify-send "WiFi" "No hay conexión WiFi"
        exit 0
    fi
    printf '{"text":" \\uf1eb ","alt":"disconnected","class":"disconnected","tooltip":"Wifi no conectada"}\n'
    exit 0
fi

net="$(printf '%s\n' "$out" | awk '{for(i=1;i<NF;i++) if($i=="network") print $(i+1)}')"

rssi="$(printf '%s\n' "$out" | awk '{for(i=1;i<NF;i++) if($i=="RSSI") print $(i+1)}')"
[ -z "$rssi" ] && rssi="$(printf '%s\n' "$out" | awk '{for(i=1;i<NF;i++) if($i=="AverageRSSI") print $(i+1)}')"

if [ -n "$rssi" ] && [ "$rssi" -le -67 ] 2>/dev/null; then
    icon="\\uf6ab"
else
    icon="\\uf1eb"
fi

if [ "$NOTIFY" = "--notify" ]; then
    if [ -n "$net" ]; then
        notify-send "WiFi" "Conectado a $net  (RSSI $rssi)"
    else
        notify-send "WiFi" "Conectado  (RSSI $rssi)"
    fi
    exit 0
fi

if [ -n "$net" ]; then
    printf '{"text":" %s ","alt":"connected","class":"connected","tooltip":"%s  (RSSI %s)"}\n' "$icon" "$net" "$rssi"
else
    printf '{"text":" %s ","alt":"connected","class":"connected","tooltip":"Conectado (RSSI %s)"}\n' "$icon" "$rssi"
fi