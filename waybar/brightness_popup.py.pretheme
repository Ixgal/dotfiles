#!/usr/bin/env python3
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

BAR_HEIGHT = 28
WIDTH = 200
PADDING = 4
TOP_BAR_MARGIN = 6
TOP_BAR_HEIGHT = 34
POPUP_GAP = 4

BACKLIGHT_DIR = "/sys/class/backlight/amdgpu_bl1"


def _read(path: str) -> int:
    try:
        with open(path) as fh:
            return int(fh.read().strip())
    except (OSError, ValueError):
        return 0


def get_brightness() -> int:
    mx = _read(f"{BACKLIGHT_DIR}/max_brightness") or 1
    act = _read(f"{BACKLIGHT_DIR}/actual_brightness")
    return int(round(act / mx * 100))


def apply_brightness(v: int) -> None:
    mx = _read(f"{BACKLIGHT_DIR}/max_brightness") or 1
    val = max(0, min(100, int(v)))
    target = int(round(val / 100 * mx))
    try:
        with open(f"{BACKLIGHT_DIR}/brightness", "w") as fh:
            fh.write(f"{target}")
    except OSError as e:
        print(f"error escribiendo brillo: {e}", file=sys.stderr)


win = Gtk.Window()
win.set_decorated(False)
win.set_resizable(False)
win.set_skip_taskbar_hint(True)
win.set_skip_pager_hint(True)
win.set_keep_above(True)
win.set_default_size(WIDTH, BAR_HEIGHT)

css = b"""
window {
    background: linear-gradient(180deg, rgba(42, 28, 78, 0.82), rgba(20, 12, 42, 0.64));
    border: 1px solid rgba(192, 132, 252, 0.35);
    border-radius: 10px;
}
scale { min-height: 14px; padding: 0 10px; }
scale trough {
    background-color: rgba(192, 132, 252, 0.18);
    border-radius: 999px;
    min-height: 5px;
    margin: 0 4px;
}
scale highlight {
    background: linear-gradient(90deg, #8b5cf6, #c084fc);
    border-radius: 999px;
    min-height: 5px;
}
scale slider {
    background-color: #d9b8ff;
    border: none;
    border-radius: 999px;
    min-height: 12px;
    min-width: 12px;
    margin: -3px 0 0 0;
    box-shadow: 0 0 8px rgba(139, 92, 246, 0.70);
}
label { color: #ede9fe; font-size: 11px; font-weight: bold; padding-right: 10px; }
"""
provider = Gtk.CssProvider()
provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(), provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
)

box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
win.add(box)

scale = Gtk.Scale(
    orientation=Gtk.Orientation.HORIZONTAL,
    adjustment=Gtk.Adjustment(
        value=get_brightness(), lower=0, upper=100, step_increment=2,
        page_increment=10, page_size=0,
    ),
)
scale.set_draw_value(False)
scale.set_size_request(140, -1)
box.pack_start(scale, True, True, 0)

label = Gtk.Label(label=f"{scale.get_value():.0f}")
box.pack_start(label, False, False, 0)

timer_id = [0]


def on_change(_scale) -> None:
    label.set_text(f"{scale.get_value():.0f}")
    if timer_id[0]:
        GLib.source_remove(timer_id[0])
    timer_id[0] = GLib.timeout_add(40, do_apply)


def do_apply() -> bool:
    timer_id[0] = 0
    apply_brightness(int(round(scale.get_value())))
    return False


def on_key(_widget, event) -> bool:
    if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Return):
        finish()
        return True
    return False


def finish() -> None:
    do_apply()
    Gtk.main_quit()


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


LOCK = "/tmp/.brightness_popup.pid"
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


def watch_hypr_events() -> None:
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
    if not sig:
        return
    runtime = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    sock_path = f"{runtime}/hypr/{sig}/.socket2.sock"
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock_path)
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
                self_a = self_addr[0] or ""
                close = False
                if ev == "activewindowv2" and addr and addr != self_a:
                    close = True
                elif ev == "openwindow" and addr != self_a:
                    close = True
                elif ev == "openlayer":
                    close = True
                if close:
                    GLib.idle_add(finish)
                    return
    except Exception:
        pass
    finally:
        try:
            s.close()
        except OSError:
            pass


def on_focus_out(_window, _event) -> bool:
    finish()
    return False


scale.connect("value-changed", on_change)
scale.connect("key-press-event", on_key)
win.connect("key-press-event", on_key)
win.connect("focus-out-event", on_focus_out)


def hypr_dispatch(*args) -> None:
    subprocess.run(["hyprctl", "dispatch", *args], capture_output=True)


def monitor_geometry_at(x: int, y: int):
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "monitors"], capture_output=True, text=True,
        ).stdout
        mons = json.loads(out or "[]")
    except Exception:
        return (0, 0, 0, 0)
    for m in mons:
        mx, my, mw, mh = m["x"], m["y"], m["width"], m["height"]
        if mx <= x < mx + mw and my <= y < my + mh:
            return mx, my, mw, mh
    if mons:
        m = mons[0]
        return m["x"], m["y"], m["width"], m["height"]
    return 0, 0, 0, 0


def hypr_cursor_pos():
    try:
        out = subprocess.run(
            ["hyprctl", "cursorpos"], capture_output=True, text=True,
        ).stdout.strip()
        x, y = map(int, out.split(","))
        return x, y
    except (ValueError, OSError):
        return 0, 0


def compute_target():
    x, y = hypr_cursor_pos()
    wx = win.get_allocated_width() or WIDTH
    mx, my, mw, mh = monitor_geometry_at(x, y)
    px = max(mx + 4, min(x - wx // 2, mx + mw - wx - 4))
    py = my + TOP_BAR_MARGIN + TOP_BAR_HEIGHT + POPUP_GAP
    return px, py, (mx, my, mw, mh)


def move_to_target(px: int, py: int, _moff, attempts: list) -> bool:
    pid = os.getpid()
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "clients"], capture_output=True, text=True,
        ).stdout
        clients = json.loads(out or "[]")
    except Exception:
        clients = []
    if any(c.get("pid") == pid for c in clients):
        hypr_dispatch("hl.dsp.window.move", f"{{ x = {px}, y = {py} }}")
        return False
    attempts[0] -= 1
    return attempts[0] > 0


def place() -> None:
    screen = win.get_screen()
    rgba = screen.get_rgba_visual()
    if rgba is not None:
        win.set_visual(rgba)
    win.set_app_paintable(True)
    win.realize()
    win.show_all()
    px, py, moff = compute_target()
    win.move(px, py)
    GLib.timeout_add(60, lambda: move_to_target(px, py, moff, [12]))


def main() -> None:
    global orig_follow_mouse
    old_pid, stored_orig = read_lock()
    if old_pid and old_pid not in (0, os.getpid()):
        try:
            os.kill(old_pid, 9)
        except (OSError, ValueError):
            pass
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
    scale.grab_focus()
    threading.Thread(target=watch_hypr_events, daemon=True).start()

    try:
        Gtk.main()
    except KeyboardInterrupt:
        sys.exit(0)
    finally:
        restore_follow_mouse()


if __name__ == "__main__":
    main()