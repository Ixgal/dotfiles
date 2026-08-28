#!/usr/bin/env python3
# Menu de energia: popup transparente anclado bajo el icono de apagado.
# Se abre desde Waybar (clic sobre el modulo custom/power) y sustituye
# al antiguo powermenu.sh (wofi centrado en pantalla).
import json
import os
import subprocess
import sys
import threading
import socket
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

WIDTH = 210
LOCK = "/tmp/.power_popup.pid"
TOP_BAR_MARGIN = 6
TOP_BAR_HEIGHT = 34
POPUP_GAP = 4
RIGHT_MARGIN = 8

# (etiqueta, icono nerd font, comando, clase css, peligroso)
ACTIONS = [
    ("Bloquear", "\uf023", ["hyprlock"], "", False),
    ("Suspender", "\uf186", ["systemctl", "suspend"], "", False),
    ("Reiniciar", "\uf021", ["systemctl", "reboot"], "", False),
    ("Apagar", "\uf011", ["systemctl", "poweroff"], "danger", True),
    ("Salir de la sesión", "\uf08b", ["hyprshutdown"], "", False),
]


def run_action(cmd) -> None:
    if cmd[0] == "hyprlock" and not shutil_which("hyprlock"):
        subprocess.Popen(["hyprctl", "dispatch", "exit"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if cmd[0] == "hyprshutdown" and not shutil_which("hyprshutdown"):
        subprocess.Popen(["hyprctl", "dispatch", "exit"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def shutil_which(cmd) -> bool:
    return subprocess.run(["command", "-v", cmd], capture_output=True).returncode == 0


win = Gtk.Window()
win.set_decorated(False)
win.set_resizable(False)
win.set_skip_taskbar_hint(True)
win.set_skip_pager_hint(True)
win.set_keep_above(True)
win.set_type_hint(Gdk.WindowTypeHint.UTILITY)
win.set_default_size(WIDTH, -1)

CSS = b"""
#menu {
    background: transparent;
}
#menu button {
    background: transparent;
    border: none;
    border-radius: 10px;
    padding: 7px 12px;
    min-height: 32px;
}
#menu button:hover {
    background: rgba(192, 132, 252, 0.18);
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.35);
}
#menu button.danger:hover {
    background: rgba(239, 68, 68, 0.20);
    box-shadow: 0 0 10px rgba(239, 68, 68, 0.30);
}
#menu label.icon {
    font-family: "Symbols Nerd Font";
    font-size: 13px;
    color: #c4b5fd;
}
#menu button.danger label.icon { color: #fca5a5; }
#menu label.text { color: #f2ecff; font-size: 12px; }
#menu button.danger label.text { color: #fecaca; }
#title { font-size: 12px; font-weight: bold; color: #ffffff; }
#close {
    background: transparent;
    border: none;
    border-radius: 999px;
    color: #8b84a8;
    font-size: 14px;
    padding: 0;
    min-height: 22px;
    min-width: 22px;
}
#close:hover { background: rgba(239, 68, 68, 0.25); color: #f87171; }
"""

provider = Gtk.CssProvider()
provider.load_from_data(CSS)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(), provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
)

# Capa comun (fondo, borde, tipografia) y animacion de apertura,
# compartidas por todos los desplegables de la barra.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_theme  # noqa: E402

popup_theme.install()

root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
root.set_name("menu")
root.set_margin_top(10)
root.set_margin_bottom(10)
root.set_margin_start(10)
root.set_margin_end(10)
win.add(root)

# --- Cabecera: titulo + cerrar ---
header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
title_lbl = Gtk.Label(label="Energía", xalign=0)
title_lbl.set_name("title")
header.pack_start(title_lbl, True, True, 0)

close_btn = Gtk.Button(label="\u2715")
close_btn.set_name("close")
close_btn.set_relief(Gtk.ReliefStyle.NONE)
close_btn.connect("clicked", lambda *a: finish())
header.pack_end(close_btn, False, False, 0)
root.pack_start(header, False, False, 0)

# --- Filas de acciones ---
for label, icon, cmd, css_class, danger in ACTIONS:
    btn = Gtk.Button()
    btn.set_relief(Gtk.ReliefStyle.NONE)
    if css_class:
        btn.get_style_context().add_class(css_class)
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    ico = Gtk.Label(label=icon)
    ico.set_name("icon")
    txt = Gtk.Label(label=label, xalign=0)
    txt.set_name("text")
    row.pack_start(ico, False, False, 0)
    row.pack_start(txt, True, True, 0)
    btn.add(row)

    def on_click(_b, cmd=cmd):
        finish()
        run_action(cmd)

    btn.connect("clicked", on_click)
    root.pack_start(btn, False, False, 0)


def finish(*_a) -> None:
    Gtk.main_quit()


def on_key(_widget, event) -> bool:
    if event.keyval == Gdk.KEY_Escape:
        finish()
        return True
    return False


def on_focus_out(_window, _event) -> bool:
    finish()
    return False


win.connect("key-press-event", on_key)
win.connect("focus-out-event", on_focus_out)
win.connect("destroy", finish)


def hypr_dispatch(*args) -> None:
    subprocess.run(["hyprctl", "dispatch", *args], capture_output=True)


def get_self_address():
    pid = os.getpid()
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "clients"], capture_output=True, text=True,
        ).stdout or "[]"
        for c in json.loads(out):
            if c.get("pid") == pid:
                return c.get("address")
    except Exception:
        pass
    return None


def watch_hypr_events() -> None:
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    if not sig:
        return
    runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(f"{runtime}/hypr/{sig}/.socket2.sock")
        s.settimeout(0.3)
    except OSError:
        return
    self_addr = [None]
    start = time.monotonic()
    buf = b""
    try:
        while True:
            try:
                data = s.recv(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if not data:
                break
            buf += data
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if time.monotonic() - start < 0.3:
                    continue
                if self_addr[0] is None:
                    self_addr[0] = get_self_address()
                    if self_addr[0] is None:
                        continue
                ev, _, rest = line.decode(errors="ignore").partition(">>")
                addr = rest.split(",")[0] if rest else ""
                if ((ev == "activewindowv2" and addr and addr != self_addr[0])
                        or (ev == "openwindow" and addr != self_addr[0])
                        or ev == "openlayer"):
                    GLib.idle_add(finish)
                    return
    except Exception:
        pass
    finally:
        try:
            s.close()
        except OSError:
            pass


orig_follow_mouse = [1]


def get_follow_mouse() -> int:
    try:
        out = subprocess.run(
            ["hyprctl", "getoption", "input:follow_mouse", "-j"],
            capture_output=True, text=True,
        ).stdout or "{}"
        return int(json.loads(out).get("int", 1))
    except Exception:
        return 1


def set_follow_mouse(v: int) -> None:
    try:
        out = subprocess.run(
            ["hyprctl", "eval", f"hl.config({{ input = {{ follow_mouse = {v} }} }})"],
            capture_output=True, text=True,
        )
        if out.returncode == 0:
            return
    except Exception:
        pass
    try:
        subprocess.run(
            ["hyprctl", "keyword", "input:follow_mouse", str(v)],
            capture_output=True,
        )
    except Exception:
        pass


def read_lock():
    try:
        with open(LOCK) as fh:
            parts = fh.read().strip().split(":")
            return int(parts[0]), int(parts[1])
    except (OSError, ValueError, IndexError):
        return None, None


def restore_follow_mouse() -> None:
    set_follow_mouse(orig_follow_mouse[0])
    try:
        with open(LOCK, "w") as fh:
            fh.write(f"0:{orig_follow_mouse[0]}")
    except OSError:
        pass


def place() -> None:
    screen = win.get_screen()
    rgba = screen.get_rgba_visual()
    if rgba is not None:
        win.set_visual(rgba)
    win.set_app_paintable(True)
    win.realize()
    popup_theme.prepare(win)
    win.show_all()
    popup_theme.fade_in(win)
    win.present()
    GLib.timeout_add(60, move_to_target, [16])


def move_to_target(attempts) -> bool:
    pid = os.getpid()
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "clients"], capture_output=True, text=True,
        ).stdout or "[]"
        clients = json.loads(out or "[]")
    except Exception:
        clients = []
    if not any(c.get("pid") == pid for c in clients):
        attempts[0] -= 1
        return attempts[0] > 0

    try:
        mons = json.loads(subprocess.run(
            ["hyprctl", "-j", "monitors"],
            capture_output=True, text=True).stdout or "[]")
    except Exception:
        mons = []
    focused = next((m for m in mons if m.get("focused")), (mons or [{}])[0])
    mx = focused.get("x") or 0
    my = focused.get("y") or 0
    mw = focused.get("width") or 1920

    ww = win.get_allocated_width() or WIDTH + 20
    # Ultimo modulo de la derecha: borde del popup alineado con el
    # margen derecho de la barra.
    px = mx + mw - ww - RIGHT_MARGIN
    py = my + TOP_BAR_MARGIN + TOP_BAR_HEIGHT + POPUP_GAP
    hypr_dispatch("hl.dsp.window.move", f"{{ x = {px}, y = {py} }}")
    return False


def main() -> None:
    global orig_follow_mouse
    old_pid, stored_orig = read_lock()
    if old_pid and old_pid not in (0, os.getpid()):
        # Segundo clic sobre el icono = cerrar el panel abierto
        try:
            os.kill(old_pid, 9)
        except (OSError, ValueError):
            pass
        orig = stored_orig if stored_orig is not None else get_follow_mouse()
        set_follow_mouse(orig)
        try:
            with open(LOCK, "w") as fh:
                fh.write(f"0:{orig}")
        except OSError:
            pass
        sys.exit(0)
    if old_pid and stored_orig is not None:
        orig_follow_mouse[0] = stored_orig
    else:
        orig_follow_mouse[0] = get_follow_mouse()
    set_follow_mouse(2)
    try:
        with open(LOCK, "w") as fh:
            fh.write(f"{os.getpid()}:{orig_follow_mouse[0]}")
    except OSError:
        pass

    place()
    win.grab_focus()
    threading.Thread(target=watch_hypr_events, daemon=True).start()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        restore_follow_mouse()


if __name__ == "__main__":
    main()
