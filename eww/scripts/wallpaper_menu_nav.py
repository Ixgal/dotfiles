#!/usr/bin/env python3
"""Navegacion por teclado del selector de fondos (menu SUPER+X).

Las flechas/Enter del submap de Hyprland llaman a este script:
  wallpaper_menu_nav.py prev|next   mover la seleccion
  wallpaper_menu_nav.py apply       aplicar la seleccion y cerrar
  wallpaper_menu_nav.py close       cerrar el menu
  wallpaper_menu_nav.py click TYPE PATH  aplicar un fondo concreto y cerrar
"""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wm_config import WINSIZE

SET_SCRIPT = Path.home() / ".config/eww/scripts/set_wallpaper.sh"
STATE_FILE = Path.home() / ".config/eww/current_wallpaper"


def eww_get(var: str) -> str:
    proc = subprocess.run(["eww", "get", var], capture_output=True, text=True)
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def eww_update(var: str, value: str) -> None:
    subprocess.run(["eww", "update", f"{var}={value}"],
                   capture_output=True)


def get_items() -> list[dict]:
    raw = eww_get("wm_items")
    try:
        items = json.loads(raw)
    except Exception:
        return []
    return items if isinstance(items, list) else []


def sel_index(items: list[dict]) -> int:
    sel = eww_get("wm_sel")
    for i, item in enumerate(items):
        if item.get("path") == sel:
            return i
    return -1


def close_menu() -> None:
    subprocess.run(["eww", "close", "wallpaper-menu"], capture_output=True)
    subprocess.run(["hyprctl", "dispatch", "hl.dsp.submap('reset')"],
                   capture_output=True)


def apply_path(typ: str, path: str) -> None:
    subprocess.Popen([str(SET_SCRIPT), typ, path])


def view_update(items: list[dict], idx: int) -> None:
    """Actualiza la ventana visible (wm_view) manteniendo la seleccion
    cerca del centro, desplazandose al navegar."""
    if not items:
        return
    n = len(items)
    if idx < 0:
        idx = 0
    if n <= WINSIZE:
        start = 0
    else:
        start = idx - (WINSIZE - 1) // 2
        start = max(0, min(start, n - WINSIZE))
    view = json.dumps(items[start:start + WINSIZE], ensure_ascii=False,
                      separators=(",", ":"))
    eww_update("wm_view", view)


def move(delta: int) -> None:
    items = get_items()
    if not items:
        return
    idx = sel_index(items)
    if delta > 0:
        idx = 0 if idx == -1 or idx >= len(items) - 1 else idx + 1
    else:
        idx = len(items) - 1 if idx <= 0 else idx - 1
    eww_update("wm_sel", items[idx].get("path", ""))
    view_update(items, idx)


def apply_selected() -> None:
    items = get_items()
    idx = sel_index(items)
    if items and idx >= 0:
        item = items[idx]
        apply_path(item.get("type", "static"), item.get("path", ""))
    close_menu()


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "prev":
        move(-1)
    elif action == "next":
        move(1)
    elif action == "sync":
        items = get_items()
        view_update(items, sel_index(items))
    elif action == "apply":
        apply_selected()
    elif action == "close":
        close_menu()
    elif action == "click" and len(sys.argv) >= 4:
        apply_path(sys.argv[2], sys.argv[3])
        close_menu()
    else:
        print(__doc__.strip())
        sys.exit(1)


if __name__ == "__main__":
    main()
