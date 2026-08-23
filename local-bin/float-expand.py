#!/usr/bin/env python3
import json
import os
import subprocess
import sys

STATE = "/tmp/hypr-float-expand-state.json"


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


def bar_bottom_for(mon_name):
    bb = 0
    for name, mon_data in (jq("layers") or {}).items():
        if name != mon_name:
            continue
        for _level, surfs in (mon_data.get("levels") or {}).items():
            for s in surfs or []:
                if s.get("namespace", "").startswith("waybar"):
                    bb = max(bb, s.get("y", 0) + s.get("h", 0))
    return bb


def main():
    win = jq("activewindow")
    if not win or not win.get("mapped", False):
        sys.exit(0)

    addr = win.get("address", "")
    sel = f'window = "address:{addr}"'
    state = load_state()

    entry = state.pop(addr, None)
    if entry:
        at = entry.get("at") or [0, 0]
        size = entry.get("size") or [0, 0]
        dispatch(f"hl.dsp.window.float({{action = 'on', {sel}}})")
        dispatch(f"hl.dsp.window.resize({{x = {size[0]}, y = {size[1]}, {sel}}})")
        dispatch(f"hl.dsp.window.move({{x = {at[0]}, y = {at[1]}, {sel}}})")
        save_state(state)
        sys.exit(0)

    qpos = win.get("at") or [0, 0]
    qsize = win.get("size") or [0, 0]
    if not (qsize[0] and qsize[1]):
        sys.exit(0)
    state[addr] = {"at": qpos, "size": qsize}

    mon = None
    for m in jq("monitors") or []:
        if m.get("id") == win.get("monitor"):
            mon = m
            break
    if mon is None:
        sys.exit(0)

    mwx, mwy = mon.get("x", 0), mon.get("y", 0)
    scale = mon.get("scale", 1.0) or 1.0
    mw = round(mon.get("width", 0) / scale)
    mh = round(mon.get("height", 0) / scale)

    block = bar_bottom_for(mon.get("name", ""))
    new_y = mwy + block
    new_h = max(1, mh - block)

    dispatch(f"hl.dsp.window.float({{action = 'on', {sel}}})")
    dispatch(f"hl.dsp.window.resize({{x = {mw}, y = {new_h}, {sel}}})")
    dispatch(f"hl.dsp.window.move({{x = {mwx}, y = {new_y}, {sel}}})")
    save_state(state)


if __name__ == "__main__":
    main()