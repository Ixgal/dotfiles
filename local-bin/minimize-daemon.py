#!/usr/bin/env python3
import asyncio
import glob
import json
import os
import re
import subprocess
import sys
import time

SPECIAL = "special:minimized"


def norm(addr):
    return addr.lower().lstrip("0x")


def instance_socket():
    d = instance_sock_dir()
    if d:
        return f"{d}/.socket2.sock"
    return None


def instance_sock_dir():
    paths = glob.glob("/run/user/*/hypr/*/")
    if paths:
        return sorted(paths)[-1].rstrip("/")
    return None


def hypr_env():
    d = instance_sock_dir()
    env = dict(os.environ)
    if d:
        env["HYPRLAND_INSTANCE_SIGNATURE"] = os.path.basename(d)
    return env


def hypr_eval(expr):
    try:
        subprocess.run(
            ["hyprctl", "eval", expr],
            capture_output=True,
            text=True,
            check=False,
            env=hypr_env(),
        )
    except Exception:
        pass


def get_window(addr):
    out = subprocess.run(
        ["hyprctl", "clients", "-j"], capture_output=True, text=True, env=hypr_env()
    )
    if out.returncode != 0:
        return None
    try:
        for w in json.loads(out.stdout):
            if norm(w.get("address", "")) == norm(addr):
                return w
    except Exception:
        pass
    return None


def window_workspace(addr):
    w = get_window(addr)
    if w:
        ws = w.get("workspace") or {}
        return {"name": ws.get("name"), "id": ws.get("id")}
    return None


def current_workspace():
    out = subprocess.run(
        ["hyprctl", "activeworkspace", "-j"],
        capture_output=True,
        text=True,
        env=hypr_env(),
    )
    if out.returncode == 0:
        try:
            d = json.loads(out.stdout)
            return d.get("id")
        except Exception:
            pass
    return 1


def minimize(addr):
    hypr_eval(
        "hl.dispatch(hl.dsp.window.move({"
        f' workspace = "{SPECIAL}", window = "address:0x{norm(addr)}", follow = false'
        "}))"
    )


def restore(addr, target):
    hypr_eval(
        "hl.dispatch(hl.dsp.window.move({"
        f' workspace = {target}, window = "address:0x{norm(addr)}", follow = false'
        "}))"
    )
    hypr_eval(
        "hl.dispatch(hl.dsp.focus({"
        f' window = "address:0x{norm(addr)}"'
        "}))"
    )


def handle(addr, state, origin):
    ws = window_workspace(addr)
    if ws is None or ws["name"] == SPECIAL:
        return
    if state:
        origin[addr] = ws
        minimize(addr)
    else:
        target = origin.pop(addr, current_workspace())
        restore(addr, target)


def handle_active(addr, origin, state):
    if state.get("active") == addr:
        w = get_window(addr)
        if not w:
            return
        ws = w.get("workspace") or {}
        if ws.get("name", "") == SPECIAL:
            target = origin.pop(addr, None)
            if target is None:
                target = state.get("normal", 1)
            if target is None:
                target = 1
            restore(addr, target)
            state["active"] = None
            return
        state["normal"] = ws.get("id")


async def watch():
    sock = instance_socket()
    if not sock:
        print("no socket", flush=True)
        return
    origin = {}
    state = {"active": None, "normal": None}
    while True:
        try:
            r, w = await asyncio.open_unix_connection(sock)
            while True:
                line = await r.readline()
                if not line:
                    break
                ev = line.decode().strip()
                m = re.match(r"^minimized>>(0x)?([0-9a-fA-F]+),(0|1)$", ev)
                if m:
                    addr = (m.group(1) or "") + m.group(2)
                    handle(addr, int(m.group(3)), origin)
                    continue
                m = re.match(r"^activewindowv2>>(0x)?([0-9a-fA-F]+)$", ev)
                if m:
                    addr = (m.group(1) or "") + m.group(2)
                    state["active"] = addr
                    handle_active(addr, origin, state)
        except Exception as e:
            pass
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(watch())