#!/usr/bin/env python3
# Mini Spotify: popup transparente estilo "mini reproductor".
# Se abre desde Waybar (clic sobre el módulo de Spotify).
import hashlib
import os
import subprocess
import sys
import threading
import socket
import json
import time
import urllib.request

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

from PIL import Image, ImageDraw, ImageOps  # noqa: E402

PLAYER = "-p"
PLAYER_NAME = "spotify"
CACHE = os.path.expanduser("~/.cache/spotify-waybar")
os.makedirs(CACHE, exist_ok=True)

WIDTH = 320
LOCK = "/tmp/.spotify_popup.pid"


def pc(*args):
    return subprocess.run(
        ["playerctl", PLAYER, PLAYER_NAME, *args],
        capture_output=True, text=True,
    )


def pc_meta_template():
    out = pc("metadata", "--format",
             '{{status}}\t{{xesam:artist}}\t{{xesam:title}}\t'
             '{{position}}\t{{mpris:length}}\t{{volume}}')
    parts = out.stdout.split("\t")
    if len(parts) < 6 or out.returncode != 0:
        return {"status": "Stopped", "artist": "", "title": "",
                "position": 0.0, "length": 0, "volume": 0.0}
    try:
        length = int(parts[4])
    except ValueError:
        length = 0
    try:
        pos = float(parts[3]) / 1_000_000  # {{position}} viene en microsegundos
    except ValueError:
        pos = 0.0
    try:
        vol = float(parts[5])
    except ValueError:
        vol = 0.0
    return {"status": parts[0], "artist": parts[1], "title": parts[2],
            "position": pos, "length": length, "volume": vol}


def fetch_art(url):
    if not url:
        return None
    key = hashlib.md5(url.encode()).hexdigest()[:16]
    cached = os.path.join(CACHE, key + ".png")
    if os.path.exists(cached):
        return cached
    src = os.path.join(CACHE, key + ".src")
    try:
        with urllib.request.urlopen(url, timeout=6) as r:
            with open(src, "wb") as fh:
                fh.write(r.read())
        im = Image.open(src).convert("RGB")
        im = ImageOps.fit(im, (256, 256), Image.LANCZOS)
        mask = Image.new("L", (256, 256), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, 256, 256],
                                               radius=24, fill=255)
        out = Image.new("RGBA", (256, 256))
        out.paste(im, (0, 0), mask)
        out.save(cached)
        os.remove(src)
        return cached
    except Exception:
        try:
            if os.path.exists(src):
                os.remove(src)
        except OSError:
            pass
        return None


# ---------------------------------------------------------------------------

win = Gtk.Window()
win.set_decorated(False)
win.set_resizable(False)
win.set_skip_taskbar_hint(True)
win.set_skip_pager_hint(True)
win.set_keep_above(True)
win.set_type_hint(Gdk.WindowTypeHint.UTILITY)

CSS = b"""
window {
    background: linear-gradient(180deg, rgba(42, 28, 78, 0.94), rgba(20, 12, 42, 0.90));
    border: 1px solid rgba(192, 132, 252, 0.30);
    border-radius: 16px;
}
#cover { border-radius: 12px; }
#title { font-size: 13px; font-weight: 700; color: #f5f3ff; }
#artist { font-size: 11px; color: #a78bfa; }
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
#time { font-size: 10px; color: #8b84a8; font-family: "Noto Sans", sans-serif; }

scale { min-height: 14px; }
scale trough {
    background-color: rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    min-height: 4px;
}
scale highlight {
    background: linear-gradient(90deg, #7d3cf6, #c084fc);
    border-radius: 999px;
    min-height: 4px;
}
scale slider {
    background-color: #e5d6ff;
    border: none;
    border-radius: 999px;
    min-height: 12px;
    min-width: 12px;
    box-shadow: 0 0 8px rgba(139, 92, 246, 0.80);
}
#progress scale slider,
#progress scale trough,
#progress scale highlight { min-height: 4px; }
#progress scale slider { min-height: 12px; min-width: 12px;}

#controls { }
#controls button {
    background: transparent;
    border: none;
    border-radius: 999px;
    color: #c4b5fd;
    font-family: "Symbols Nerd Font";
    padding: 0;
}
#controls button:hover {
    background: rgba(192, 132, 252, 0.18);
    color: #ffffff;
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.35);
}
#ctrl-skip { font-size: 20px; min-height: 38px; min-width: 44px; }
#ctrl-play { font-size: 24px; min-height: 46px; min-width: 52px; }
#vol-icon { font-family: "Symbols Nerd Font"; font-size: 13px; color: #c084fc; }
#open {
    background: transparent;
    border: none;
    color: #8b84a8;
    font-size: 10px;
    padding: 2px;
}
#open:hover { color: #ffffff; text-decoration: underline; }
"""

provider = Gtk.CssProvider()
provider.load_from_data(CSS)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(), provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
)

root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
root.set_margin_top(14)
root.set_margin_bottom(14)
root.set_margin_start(16)
root.set_margin_end(16)
win.add(root)

# --- Cabecera: carátula + info + cerrar ---
header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
cover = Gtk.Image()
cover.set_size_request(62, 62)
cover_box = Gtk.EventBox()
cover_box.add(cover)
cover_box.set_name("cover-box")
header.pack_start(cover_box, False, False, 0)

info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
title_lbl = Gtk.Label(label="Spotify", xalign=0)
title_lbl.set_name("title")
title_lbl.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
artist_lbl = Gtk.Label(label="", xalign=0)
artist_lbl.set_name("artist")
artist_lbl.set_ellipsize(3)
info.pack_start(title_lbl, False, False, 0)
info.pack_start(artist_lbl, False, False, 0)
header.pack_start(info, True, True, 0)

close_btn = Gtk.Button(label="\u2715")
close_btn.set_name("close")
close_btn.set_relief(Gtk.ReliefStyle.NONE)
close_btn.connect("clicked", lambda *a: finish())
header.pack_end(close_btn, False, False, 0)
root.pack_start(header, False, False, 0)

# --- Progreso + tiempos ---
progress_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
elapsed = Gtk.Label(label="0:00", xalign=1)
elapsed.set_name("time")
total = Gtk.Label(label="0:00", xalign=0)
total.set_name("time")
prog = Gtk.Scale(
    orientation=Gtk.Orientation.HORIZONTAL,
    adjustment=Gtk.Adjustment(value=0, lower=0, upper=100,
                              step_increment=1, page_increment=10, page_size=0),
)
prog.set_draw_value(False)
prog.set_hexpand(True)
prog.set_size_request(-1, 10)
progress_row.pack_start(elapsed, False, False, 0)
progress_row.pack_start(prog, True, True, 0)
progress_row.pack_start(total, False, False, 0)
root.pack_start(progress_row, False, False, 0)

# --- Controles ---
controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
controls.set_halign(Gtk.Align.CENTER)
controls.set_valign(Gtk.Align.CENTER)
btn_prev = Gtk.Button(label="\uf048")
btn_prev.set_name("ctrl-skip")
btn_prev.set_size_request(42, 40)
btn_play = Gtk.Button(label="\uf04c")
btn_play.set_name("ctrl-play")
btn_play.set_size_request(54, 48)
btn_next = Gtk.Button(label="\uf049")
btn_next.set_name("ctrl-skip")
btn_next.set_size_request(42, 40)
controls.pack_start(btn_prev, False, False, 0)
controls.pack_start(btn_play, False, False, 0)
controls.pack_start(btn_next, False, False, 0)
root.pack_start(controls, False, False, 0)

# --- Volumen ---
vol_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
vol_icon = Gtk.Label(label="\uf028")
vol_icon.set_name("vol-icon")
vol_row.pack_start(vol_icon, False, False, 0)
vol_scale = Gtk.Scale(
    orientation=Gtk.Orientation.HORIZONTAL,
    adjustment=Gtk.Adjustment(value=50, lower=0, upper=100,
                              step_increment=2, page_increment=10, page_size=0),
)
vol_scale.set_draw_value(False)
vol_scale.set_hexpand(True)
vol_row.pack_start(vol_scale, True, True, 0)
root.pack_start(vol_row, False, False, 0)

# --- Abrir Spotify ---
open_btn = Gtk.Button(label="Abrir Spotify  \uf1bc")
open_btn.set_name("open")
open_btn.set_halign(Gtk.Align.CENTER)
open_btn.connect("clicked", lambda *a: subprocess.Popen(
    ["flatpak", "run", "com.spotify.Client"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
root.pack_start(open_btn, False, False, 0)

# ---------------------------------------------------------------------------


dragging = {"prog": False, "vol": False, "muted": False}
vol_timer = [0]


def fmt(s):
    s = max(0, int(s))
    return f"{s // 60}:{s % 60:02d}"


def set_progress_adj():
    d = pc_meta_template()
    length_s = max(1, d["length"] // 1_000_000)
    adj = prog.get_adjustment()
    adj.configure(d["position"], 0, length_s, 1, 60, 0)
    if not dragging["prog"]:
        prog.set_value(d["position"])
    elapsed.set_text(fmt(d["position"]))
    total.set_text(fmt(length_s))


def apply_vol_now():
    v = vol_scale.get_value()
    pc("volume", f"{v / 100:.2f}")


def on_vol_change(_scale):
    global vol_timer
    if vol_timer[0]:
        GLib.source_remove(vol_timer[0])
    vol_timer[0] = GLib.timeout_add(120, do_apply_vol)
    draw_vol_icon()


def do_apply_vol():
    vol_timer[0] = 0
    apply_vol_now()
    return False


def draw_vol_icon():
    if dragging["muted"]:
        vol_icon.set_text("\uf6a9")
        return
    v = vol_scale.get_value()
    if v <= 0:
        vol_icon.set_text("\uf026")
    elif v < 55:
        vol_icon.set_text("\uf027")
    else:
        vol_icon.set_text("\uf028")


def on_vol_press(_w, ev):
    dragging["vol"] = True
    return False


def on_vol_release(_w, ev):
    dragging["vol"] = False
    apply_vol_now()
    return False


vol_scale.connect("value-changed", on_vol_change)
vol_scale.connect("button-press-event", on_vol_press)
vol_scale.connect("button-release-event", on_vol_release)
vol_scale.connect("scroll-event", lambda *a: False)


def on_prog_press(_w, ev):
    dragging["prog"] = True
    return False


def on_prog_release(_w, ev):
    dragging["prog"] = False
    pc("position", str(prog.get_value()))
    return False


prog.connect("button-press-event", on_prog_press)
prog.connect("button-release-event", on_prog_release)

btn_prev.connect("clicked", lambda *a: pc("previous"))
btn_next.connect("clicked", lambda *a: pc("next"))


def on_play_click(*_a):
    pc("play-pause")


btn_play.connect("clicked", on_play_click)

# ---------------------------------------------------------------------------

art = {"url": None, "file": None}


def refresh(_=None):
    d = pc_meta_template()
    title_lbl.set_text(d["title"] or "Spotify")
    artist_lbl.set_text(d["artist"] or "")
    btn_play.set_label("\uf04b" if d["status"] != "Playing" else "\uf04c")
    if not dragging["vol"]:
        vol_scale.set_value(d["volume"] * 100)
    if not dragging["prog"]:
        set_progress_adj()
    url = pc("metadata", "--format", "{{mpris:artUrl}}").stdout.strip()
    if url != art["url"]:
        art["url"] = url
        update_art(url)
    return True


def update_art(url):
    f = fetch_art(url)
    art["file"] = f
    if f:
        try:
            from gi.repository import GdkPixbuf
            pb = GdkPixbuf.Pixbuf.new_from_file(f)
            if pb.get_width() > 62:
                pb = pb.scale_simple(62, 62, GdkPixbuf.InterpType.BILINEAR)
            cover.set_from_pixbuf(pb)
        except Exception:
            cover.set_from_file("")
            cover.clear()
    else:
        cover.clear()


def on_key(_widget, event):
    if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Return):
        finish()
        return True
    if event.keyval == Gdk.KEY_space:
        pc("play-pause")
        return True
    return False


def finish():
    try:
        Gtk.main_quit()
    except Exception:
        pass


def on_focus_out(_window, _event):
    finish()
    return False


win.connect("key-press-event", on_key)
win.connect("focus-out-event", on_focus_out)

# --- Posicionamiento / enfoque (patrón del volumen popup) ---


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


orig_follow_mouse = [1]


def get_follow_mouse():
    try:
        out = subprocess.run(
            ["hyprctl", "getoption", "input:follow_mouse", "-j"],
            capture_output=True, text=True,
        ).stdout or "{}"
        return int(json.loads(out).get("int", 1))
    except Exception:
        return 1


def set_follow_mouse(v):
    try:
        subprocess.run(["hyprctl", "eval", f"hl.config({{ input = {{ follow_mouse = {v} }} }})"],
                       capture_output=True)
    except Exception:
        pass


def restore_follow_mouse():
    set_follow_mouse(orig_follow_mouse[0])
    try:
        with open(LOCK, "w") as fh:
            fh.write(f"0:{orig_follow_mouse[0]}")
    except OSError:
        pass


def read_lock():
    try:
        with open(LOCK) as fh:
            parts = fh.read().strip().split(":")
            return int(parts[0]), int(parts[1])
    except (OSError, ValueError, IndexError):
        return None, None


def watch_hypr_events():
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
                self_a = self_addr[0] or ""
                if ev == "openlayer":
                    GLib.idle_add(finish)
                    return
                if (ev in ("activewindowv2", "openwindow") and addr and addr != self_a):
                    GLib.idle_add(finish)
                    return
    except Exception:
        pass
    finally:
        try:
            s.close()
        except OSError:
            pass


def hypr_monitors():
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "monitors"], capture_output=True, text=True,
        ).stdout
        return json.loads(out or "[]")
    except Exception:
        return []


def hypr_dispatch(*args):
    subprocess.run(["hyprctl", "dispatch", *args], capture_output=True)


def place():
    screen = win.get_screen()
    rgba = screen.get_rgba_visual()
    if rgba is not None:
        win.set_visual(rgba)
    win.set_app_paintable(True)
    win.realize()
    win.show_all()
    win.present()

    # Espera a que Wayland registre la ventana y la mueve junto al icono.
    GLib.timeout_add(60, move_to_target, [16])


def move_to_target(attempts):
    pid = os.getpid()
    try:
        out = subprocess.run(
            ["hyprctl", "-j", "clients"], capture_output=True, text=True,
        ).stdout or "[]"
        clients = json.loads(out or "[]")
    except Exception:
        clients = []
    found = next((c for c in clients if c.get("pid") == pid), None)
    if not found:
        attempts[0] -= 1
        return attempts[0] > 0

    mons = hypr_monitors()
    focused = next((m for m in mons if m.get("focused")), (mons or [{}])[0])
    mx = focused.get("x") or 0
    my = focused.get("y") or 0
    mw = focused.get("width") or 1920

    W = win.get_allocated_width() or WIDTH + 32
    # Justo debajo del módulo de Spotify: barra derecha, antes del botón de apagado.
    px = mx + mw - W - 48
    py = my + 44
    hypr_dispatch("hl.dsp.window.move", f"{{ x = {px}, y = {py} }}")
    return False


def main():
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
    refresh()
    GLib.timeout_add(800, refresh)
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