#!/usr/bin/env python3
"""Panel de estadisticas del sistema en tiempo real.

Sustituye al drawer horizontal de waybar (que se desplegaba hacia la
izquierda y solo cabian cuatro cifras): se abre DEBAJO de la barra, con
el mismo cristal morado, y refresca cada segundo.
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

WIDTH = 330
TOP_BAR_MARGIN = 6
TOP_BAR_HEIGHT = 34
POPUP_GAP = 4
REFRESH_MS = 1000
LOCK = "/tmp/.system_popup.pid"

# ---------------------------------------------------------------- lecturas


def _read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ""


def cpu_times():
    """(idle, total) agregados y por nucleo, desde /proc/stat."""
    out = []
    for line in _read("/proc/stat").splitlines():
        if not line.startswith("cpu"):
            break
        parts = line.split()
        vals = [int(v) for v in parts[1:]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        out.append((idle, sum(vals)))
    return out


def cpu_percent(prev, cur):
    res = []
    for (pi, pt), (ci, ct) in zip(prev, cur):
        dt = ct - pt
        di = ci - pi
        res.append(0.0 if dt <= 0 else max(0.0, min(100.0, (1 - di / dt) * 100)))
    return res


def cpu_mhz():
    vals = [float(l.split(":")[1]) for l in _read("/proc/cpuinfo").splitlines()
            if l.startswith("cpu MHz")]
    return sum(vals) / len(vals) if vals else 0.0


def meminfo():
    d = {}
    for line in _read("/proc/meminfo").splitlines():
        k, _, v = line.partition(":")
        d[k] = int(v.split()[0]) * 1024 if v.split() else 0
    total = d.get("MemTotal", 0)
    avail = d.get("MemAvailable", 0)
    sw_t = d.get("SwapTotal", 0)
    sw_f = d.get("SwapFree", 0)
    return total, total - avail, sw_t, sw_t - sw_f


def net_bytes():
    rx = tx = 0
    for line in _read("/proc/net/dev").splitlines()[2:]:
        iface, _, rest = line.partition(":")
        iface = iface.strip()
        if iface == "lo" or iface.startswith(("veth", "docker", "br-")):
            continue
        f = rest.split()
        if len(f) >= 9:
            rx += int(f[0])
            tx += int(f[8])
    return rx, tx


def temperatures():
    """Sensores hwmon relevantes: CPU y GPU."""
    out = []
    base = "/sys/class/hwmon"
    try:
        hwmons = sorted(os.listdir(base))
    except OSError:
        return out
    for hw in hwmons:
        name = _read(f"{base}/{hw}/name").strip()
        if name not in ("k10temp", "coretemp", "zenpower", "amdgpu", "nvme",
                        "acpitz", "cpu_thermal"):
            continue
        d = f"{base}/{hw}"
        try:
            inputs = sorted(f for f in os.listdir(d)
                            if f.startswith("temp") and f.endswith("_input"))
        except OSError:
            continue
        for inp in inputs[:2]:
            raw = _read(f"{d}/{inp}").strip()
            if not raw:
                continue
            label = _read(f"{d}/{inp.replace('_input', '_label')}").strip()
            pretty = {"k10temp": "CPU", "zenpower": "CPU", "coretemp": "CPU",
                      "amdgpu": "GPU", "nvme": "SSD", "acpitz": "Placa",
                      "cpu_thermal": "CPU"}[name]
            if label and label.lower() not in ("tctl", "composite", "edge"):
                pretty = f"{pretty} {label}"
            try:
                out.append((pretty, int(raw) / 1000))
            except ValueError:
                pass
    return out


def uptime_str():
    try:
        secs = int(float(_read("/proc/uptime").split()[0]))
    except (IndexError, ValueError):
        return "?"
    d, rem = divmod(secs, 86400)
    h, rem = divmod(rem, 3600)
    m = rem // 60
    if d:
        return f"{d}d {h}h {m}m"
    return f"{h}h {m}m" if h else f"{m}m"


def human(n):
    for unit in ("B", "K", "M", "G", "T"):
        if abs(n) < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}P"


# ---------------------------------------------------------------- interfaz

win = Gtk.Window()
win.set_decorated(False)
win.set_resizable(False)
win.set_skip_taskbar_hint(True)
win.set_skip_pager_hint(True)
win.set_keep_above(True)
win.set_default_size(WIDTH, -1)

css = b"""
window {
    background: linear-gradient(180deg, rgba(59, 44, 105, 0.97), rgba(28, 17, 56, 0.95));
    border: 1px solid rgba(109, 58, 192, 0.90);
    border-radius: 12px;
}
label { color: #f2ecff; font-size: 11px; }
label.title { font-size: 12px; font-weight: bold; color: #ffffff; }
label.key { color: #cfc4ea; }
label.val { font-weight: bold; color: #ffffff; }
label.hint { color: #b0a4d0; font-size: 10px; }
levelbar block.filled {
    background: linear-gradient(90deg, #8b5cf6, #d8b4fe);
    border-radius: 999px;
    border: none;
}
levelbar block.empty {
    background-color: rgba(216, 180, 254, 0.15);
    border-radius: 999px;
    border: none;
}
levelbar trough {
    background: transparent;
    border: none;
    padding: 0;
    min-height: 6px;
}
separator { background-color: rgba(216, 180, 254, 0.20); min-height: 1px; }
"""
provider = Gtk.CssProvider()
provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(), provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
)

# Capa comun (fondo, borde, tipografia, sliders) y animacion de apertura,
# compartidas por todos los desplegables de la barra.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import popup_theme  # noqa: E402

popup_theme.install()

root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
root.set_margin_top(11)
root.set_margin_bottom(11)
root.set_margin_start(13)
root.set_margin_end(13)
win.add(root)


def styled(widget, name):
    widget.get_style_context().add_class(name)
    return widget


def add_title(text):
    lbl = styled(Gtk.Label(label=text, xalign=0), "title")
    root.pack_start(lbl, False, False, 0)
    return lbl


def add_bar_row(key):
    """Fila: nombre + valor a la derecha, con barra debajo."""
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    k = styled(Gtk.Label(label=key, xalign=0), "key")
    v = styled(Gtk.Label(label="", xalign=1), "val")
    head.pack_start(k, False, False, 0)
    head.pack_end(v, False, False, 0)
    bar = Gtk.LevelBar()
    bar.set_min_value(0)
    bar.set_max_value(100)
    bar.set_mode(Gtk.LevelBarMode.CONTINUOUS)
    bar.set_size_request(-1, 6)
    box.pack_start(head, False, False, 0)
    box.pack_start(bar, False, False, 0)
    root.pack_start(box, False, False, 0)
    return v, bar


def add_kv_row(key):
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
    box.pack_start(styled(Gtk.Label(label=key, xalign=0), "key"), False, False, 0)
    v = styled(Gtk.Label(label="", xalign=1), "val")
    box.pack_end(v, False, False, 0)
    root.pack_start(box, False, False, 0)
    return v


def add_sep():
    root.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL),
                    False, False, 3)


add_title("Sistema")
cpu_val, cpu_bar = add_bar_row("CPU")

# Una barra fina por nucleo
cores_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
core_bars = []
n_cores = max(1, len(cpu_times()) - 1)
for _ in range(n_cores):
    b = Gtk.LevelBar()
    b.set_min_value(0)
    b.set_max_value(100)
    b.set_mode(Gtk.LevelBarMode.CONTINUOUS)
    b.set_orientation(Gtk.Orientation.HORIZONTAL)
    b.set_size_request(-1, 4)
    cores_box.pack_start(b, True, True, 0)
    core_bars.append(b)
root.pack_start(cores_box, False, False, 0)

freq_val = add_kv_row("Frecuencia")
add_sep()

ram_val, ram_bar = add_bar_row("Memoria")
swap_val = add_kv_row("Swap")
add_sep()

disk_val, disk_bar = add_bar_row("Disco  /")
add_sep()

temp_rows = {}
net_val = add_kv_row("Red")
load_val = add_kv_row("Carga")
up_val = add_kv_row("Encendido")

hint = styled(Gtk.Label(label="Esc para cerrar", xalign=0), "hint")
root.pack_start(hint, False, False, 0)

state = {
    "cpu": cpu_times(),
    "net": net_bytes(),
    "t": time.monotonic(),
    "temps_built": False,
}


def build_temp_rows(temps):
    """Las filas de sensores se crean una vez, al primer refresco."""
    for name, _ in temps:
        if name in temp_rows:
            continue
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.pack_start(styled(Gtk.Label(label=f"Temp {name}", xalign=0), "key"),
                       False, False, 0)
        v = styled(Gtk.Label(label="", xalign=1), "val")
        box.pack_end(v, False, False, 0)
        # Insertar antes de las filas de red/carga/uptime
        root.pack_start(box, False, False, 0)
        root.reorder_child(box, len(root.get_children()) - 5)
        temp_rows[name] = v
        box.show_all()


def refresh():
    now = time.monotonic()
    dt = max(0.2, now - state["t"])

    cur = cpu_times()
    pcts = cpu_percent(state["cpu"], cur)
    state["cpu"] = cur
    if pcts:
        cpu_val.set_text(f"{pcts[0]:.0f}%")
        cpu_bar.set_value(pcts[0])
        for bar, p in zip(core_bars, pcts[1:]):
            bar.set_value(p)
    freq_val.set_text(f"{cpu_mhz() / 1000:.2f} GHz")

    total, used, sw_t, sw_u = meminfo()
    if total:
        ram_val.set_text(f"{human(used)} / {human(total)}  ({used / total * 100:.0f}%)")
        ram_bar.set_value(used / total * 100)
    swap_val.set_text(
        f"{human(sw_u)} / {human(sw_t)}" if sw_t else "sin swap")

    try:
        du = shutil.disk_usage("/")
        disk_val.set_text(
            f"{human(du.used)} / {human(du.total)}  ({du.used / du.total * 100:.0f}%)")
        disk_bar.set_value(du.used / du.total * 100)
    except OSError:
        disk_val.set_text("?")

    temps = temperatures()
    if not state["temps_built"] and temps:
        build_temp_rows(temps)
        state["temps_built"] = True
    for name, val in temps:
        if name in temp_rows:
            temp_rows[name].set_text(f"{val:.0f} °C")

    rx, tx = net_bytes()
    prx, ptx = state["net"]
    state["net"] = (rx, tx)
    net_val.set_text(f"↓ {human((rx - prx) / dt)}/s   ↑ {human((tx - ptx) / dt)}/s")

    load = _read("/proc/loadavg").split()[:3]
    load_val.set_text("  ".join(load) if load else "?")
    up_val.set_text(uptime_str())

    state["t"] = now
    return True


# ------------------------------------------------- colocacion y cierre


def finish(*_a):
    Gtk.main_quit()


def on_key(_w, event):
    if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Return):
        finish()
        return True
    return False


def on_focus_out(_w, _e):
    finish()
    return False


win.connect("key-press-event", on_key)
win.connect("focus-out-event", on_focus_out)
win.connect("destroy", finish)


def get_self_address():
    pid = os.getpid()
    try:
        out = subprocess.run(["hyprctl", "-j", "clients"],
                             capture_output=True, text=True).stdout or "[]"
        for c in json.loads(out):
            if c.get("pid") == pid:
                return c.get("address")
    except Exception:
        pass
    return None


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


def hypr_cursor_pos():
    try:
        out = subprocess.run(["hyprctl", "cursorpos"],
                             capture_output=True, text=True).stdout.strip()
        x, y = map(int, out.split(","))
        return x, y
    except (ValueError, OSError):
        return 0, 0


def monitor_geometry_at(x, y):
    try:
        mons = json.loads(subprocess.run(
            ["hyprctl", "-j", "monitors"],
            capture_output=True, text=True).stdout or "[]")
    except Exception:
        return (0, 0, 1920, 1080)
    for m in mons:
        if m["x"] <= x < m["x"] + m["width"] and m["y"] <= y < m["y"] + m["height"]:
            return m["x"], m["y"], m["width"], m["height"]
    if mons:
        m = mons[0]
        return m["x"], m["y"], m["width"], m["height"]
    return (0, 0, 1920, 1080)


def compute_target():
    x, y = hypr_cursor_pos()
    ww = win.get_allocated_width() or WIDTH
    mx, my, mw, mh = monitor_geometry_at(x, y)
    px = max(mx + 6, min(x - ww // 2, mx + mw - ww - 6))
    py = my + TOP_BAR_MARGIN + TOP_BAR_HEIGHT + POPUP_GAP
    return px, py


def move_to_target(px, py, attempts):
    pid = os.getpid()
    try:
        clients = json.loads(subprocess.run(
            ["hyprctl", "-j", "clients"],
            capture_output=True, text=True).stdout or "[]")
    except Exception:
        clients = []
    if any(c.get("pid") == pid for c in clients):
        subprocess.run(["hyprctl", "dispatch", "hl.dsp.window.move",
                        f"{{ x = {px}, y = {py} }}"], capture_output=True)
        return False
    attempts[0] -= 1
    return attempts[0] > 0


def place():
    screen = win.get_screen()
    rgba = screen.get_rgba_visual()
    if rgba is not None:
        win.set_visual(rgba)
    win.set_app_paintable(True)
    win.realize()
    popup_theme.prepare(win)
    win.show_all()
    popup_theme.fade_in(win)
    px, py = compute_target()
    win.move(px, py)
    GLib.timeout_add(60, lambda: move_to_target(px, py, [12]))


def main():
    # Segundo clic sobre el icono = cerrar el panel abierto
    try:
        with open(LOCK) as fh:
            old = int(fh.read().strip())
        if old and old != os.getpid():
            os.kill(old, 9)
            sys.exit(0)
    except (OSError, ValueError, ProcessLookupError):
        pass
    try:
        with open(LOCK, "w") as fh:
            fh.write(str(os.getpid()))
    except OSError:
        pass

    refresh()
    place()
    win.grab_focus()
    GLib.timeout_add(REFRESH_MS, refresh)
    threading.Thread(target=watch_hypr_events, daemon=True).start()
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            os.unlink(LOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
