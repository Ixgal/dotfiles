#!/usr/bin/env python3
import json
import subprocess
import sys

STATE = "/tmp/hypr-window-expand-state.json"


def jq(what):
    out = subprocess.run(["hyprctl", what, "-j"], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except Exception:
        return None


def dispatch(expr):
    subprocess.run(["hyprctl", "dispatch", expr], capture_output=True, text=True)


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


def window_under_cursor():
    cur = jq("cursorpos")
    if not cur:
        return None
    cx, cy = cur.get("x", -1), cur.get("y", -1)
    best = None
    for w in jq("clients") or []:
        if not w.get("mapped", False):
            continue
        x, y = w.get("at") or [0, 0]
        ww, wh = w.get("size") or [0, 0]
        if x <= cx < x + ww and y <= cy < y + wh:
            if w.get("floating", False):
                return w
            if best is None:
                best = w
    return best


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


def sel(addr):
    return f'window = "address:{addr}"'


def main():
    win = window_under_cursor()
    if not win:
        sys.exit(0)
    addr = win.get("address", "")
    if not addr:
        sys.exit(0)
    if win.get("fullscreen", False):
        sys.exit(0)

    state = load_state()
    entry = state.pop(addr, None)
    if entry:
        if entry.get("tiled"):
            dispatch(f"hl.dsp.window.float({{action = 'off', {sel(addr)}}})")
        else:
            dispatch(f"hl.dsp.window.float({{action = 'on', {sel(addr)}}})")
            dispatch(f"hl.dsp.window.resize({{x = {entry['size'][0]}, y = {entry['size'][1]}, {sel(addr)}}})")
            dispatch(f"hl.dsp.window.move({{x = {entry['at'][0]}, y = {entry['at'][1]}, {sel(addr)}}})")
        save_state(state)
        sys.exit(0)

    mon = None
    for m in jq("monitors") or []:
        if m.get("id") == win.get("monitor"):
            mon = m
            break
    if mon is None:
        sys.exit(0)

    state[addr] = {"at": win.get("at"), "size": win.get("size"), "tiled": not win.get("floating", False)}
    ax, ay, aw, ah = work_area(mon)
    dispatch(f"hl.dsp.window.float({{action = 'on', {sel(addr)}}})")
    dispatch(f"hl.dsp.window.resize({{x = {aw}, y = {ah}, {sel(addr)}}})")
    dispatch(f"hl.dsp.window.move({{x = {ax}, y = {ay}, {sel(addr)}}})")
    dispatch(f"hl.dsp.window.alter_zorder({{mode = 'top', {sel(addr)}}})")
    save_state(state)


if __name__ == "__main__":
    main()
