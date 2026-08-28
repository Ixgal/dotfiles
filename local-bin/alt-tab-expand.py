#!/usr/bin/env python3
import fcntl
import json
import subprocess
import sys

STATE = "/tmp/hypr-window-expand-state.json"
LOCK = "/tmp/hypr-window-expand.lock"
LOG = "/tmp/hypr-window-expand.log"
TOL = 24


def log(msg):
    try:
        with open(LOG, "a") as f:
            import time
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def jq(what):
    out = subprocess.run(["hyprctl", what, "-j"], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except Exception:
        return None


def dispatch_batch(exprs):
    batch = "; ".join(f"dispatch {e}" for e in exprs)
    subprocess.run(["hyprctl", "--batch", batch], capture_output=True, text=True)


def load_state():
    try:
        with open(STATE) as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(state):
    try:
        with open(STATE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass


def sel(addr):
    return f'window = "address:{addr}"'


def work_area(mon):
    scale = mon.get("scale", 1.0) or 1.0
    mw = round(mon.get("width", 0) / scale)
    mh = round(mon.get("height", 0) / scale)
    mwx = mon.get("x", 0)
    mwy = mon.get("y", 0)
    top = 0
    bottom = mh
    for name, mdata in (jq("layers") or {}).items():
        if name != mon.get("name"):
            continue
        for _level, surfs in (mdata.get("levels") or {}).items():
            for s in surfs or []:
                if not (s.get("namespace") or "").startswith("waybar"):
                    continue
                y = s.get("y", 0)
                h = s.get("h", 0)
                rel = y - mwy
                if rel + h / 2 < mh / 2:
                    top = max(top, rel + h)
                else:
                    bottom = min(bottom, rel)
    return mwx, mwy + top, mw, max(1, bottom - top)


def is_expanded(win, wa):
    if not win.get("floating", False):
        return False
    ax, ay, aw, ah = wa
    wx, wy = win.get("at") or [0, 0]
    ww, wh = win.get("size") or [0, 0]
    return abs(wx - ax) <= TOL and abs(wy - ay) <= TOL and abs(ww - aw) <= TOL and abs(wh - ah) <= TOL


def main():
    prev = "--prev" in sys.argv
    lock_f = open(LOCK, "w")
    fcntl.flock(lock_f, fcntl.LOCK_EX)
    try:
        before = (jq("activewindow") or {}).get("address")
        before_fs = False
        if before:
            bw = next((w for w in jq("clients") or [] if w.get("address") == before), None)
            before_fs = bool(bw and bw.get("fullscreen", 0))
        if prev:
            dispatch_batch(["hl.dsp.window.cycle_next({ next = false })"])
        else:
            dispatch_batch(["hl.dsp.window.cycle_next()"])
        win = jq("activewindow") or {}
        addr = win.get("address", "")
        if not addr or addr == before:
            log("alt-tab: no hay otra ventana que ciclar")
            return
        if before_fs:
            # cyclenext saca de fullscreen a la ventana de la que venimos
            # (comportamiento de Hyprland); se lo devolvemos para que el juego
            # siga fullscreen detras de la ventana recien enfocada.
            bw = next((w for w in jq("clients") or [] if w.get("address") == before), None)
            if bw and not bw.get("fullscreen", 0):
                log(f"alt-tab: devolver fullscreen a {bw.get('class')} (cycle_next se lo quito)")
                dispatch_batch([f"hl.dsp.window.fullscreen({{action = 'toggle', {sel(before)}}})"])
        if not win.get("mapped", False):
            log("alt-tab: ventana no mapeada")
            return
        if win.get("fullscreen", False):
            log(f"alt-tab: {win.get('class')} es fullscreen -> se sube al frente (prioridad al juego)")
            exprs = [f"hl.dsp.window.alter_zorder({{mode = 'top', {sel(addr)}}})"]
            ws_id = (win.get("workspace") or {}).get("id")
            for w in jq("clients") or []:
                a = w.get("address")
                if a == addr or not w.get("mapped", False) or not w.get("floating", False):
                    continue
                if ws_id is not None and (w.get("workspace") or {}).get("id") != ws_id:
                    continue
                if not w.get("allowedOverFullscreen", False):
                    continue
                exprs.append(f"hl.dsp.window.alter_zorder({{mode = 'bottom', {sel(a)}}})")
            dispatch_batch(exprs)
            return
        mon = None
        for m in jq("monitors") or []:
            if m.get("id") == win.get("monitor"):
                mon = m
                break
        if mon is None:
            return
        wa = work_area(mon)
        if is_expanded(win, wa):
            log(f"alt-tab: {win.get('class')} ya estaba expandida -> se sube al frente")
            dispatch_batch([f"hl.dsp.window.alter_zorder({{mode = 'top', {sel(addr)}}})"])
            return
        state = load_state()
        if addr not in state:
            state[addr] = {"at": win.get("at"), "size": win.get("size"), "tiled": not win.get("floating", False)}
            save_state(state)
        ax, ay, aw, ah = wa
        log(f"alt-tab: expandir {win.get('class')} a {aw}x{ah}@{ax},{ay} (ya enfocada por cycle)")
        dispatch_batch([
            f"hl.dsp.window.float({{action = 'on', {sel(addr)}}})",
            f"hl.dsp.window.resize({{x = {aw}, y = {ah}, {sel(addr)}}})",
            f"hl.dsp.window.move({{x = {ax}, y = {ay}, {sel(addr)}}})",
            f"hl.dsp.window.alter_zorder({{mode = 'top', {sel(addr)}}})",
        ])
    finally:
        fcntl.flock(lock_f, fcntl.LOCK_UN)
        lock_f.close()


if __name__ == "__main__":
    main()
