#!/usr/bin/env python3
"""Genera eww.yuck con la lista de fondos de pantalla incrustada
de forma estatica (sin defpoll/literal), para que SUPER+W siempre
muestre las miniaturas de inmediato."""
import json
import sys
from pathlib import Path

WE_DIR = Path.home() / ".local/share/Steam/steamapps/workshop/content/431960"
STATIC_DIR = Path.home() / "Pictures/Wallpapers"
ANIM_DIR = Path.home() / "Pictures/Wallpapers/animados"
GENRES_DIR = Path.home() / "Pictures/Wallpapers/genres"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".avif"}
PLACEHOLDER = str(Path(__file__).parent / "placeholder.png")
SCRIPT = "/home/jairo/.config/eww/scripts/set_wallpaper.sh"
YUCK = Path(__file__).parent.parent / "eww.yuck"

WINDOW_TEMPLATE = """(defwindow wallpaper-menu
  :monitor 0
  :geometry (geometry
             :x "0px"
             :y "0px"
             :anchor "top right"
             :width "260px"
             :height "480px")
  :stacking "overlay"
  :windowtype "normal"
  :focusable true
  (box
    :class "wallpaper-menu"
    :orientation "v"
    (box
      :class "wallpaper-header"
      :orientation "h"
      (label :class "wallpaper-title" :text "Fondos" :halign "start")
      (button
        :class "wallpaper-close"
        :onclick "eww close wallpaper-menu"
        "✕"))
    (scroll
      :class "wallpaper-scroll"
      :vscroll true
      :hscroll false
      :width 232
      :height 400
      __CONTENT__)))"""


def esc(s: str) -> str:
    """Escapa un valor para usarlo entre comillas dobles en yuck."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def first_image(folder: Path):
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in IMG_EXTS:
            return f
    return None


def we_preview(folder: Path):
    pj = folder / "project.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text())
            prev = data.get("preview")
            if prev:
                cand = folder / prev
                if cand.exists():
                    return str(cand)
        except Exception:
            pass
    for f in sorted(folder.iterdir()):
        if f.is_file() and f.suffix.lower() in IMG_EXTS and "preview" in f.name.lower():
            return str(f)
    img = first_image(folder)
    return str(img) if img else None


def we_name(folder: Path, wfid: str) -> str:
    pj = folder / "project.json"
    if pj.exists():
        try:
            data = json.loads(pj.read_text())
            for key in ("title", "name"):
                val = data.get(key)
                if val:
                    return str(val)
        except Exception:
            pass
    return wfid


def build_items(items):
    """Genera el yuck de cada elemento de la lista."""
    out = []
    for it in items:
        wtype = it["type"]
        wid = esc(it["id"])
        preview = esc(it.get("preview") or PLACEHOLDER)
        name = esc(it["name"])
        onclick = f"{SCRIPT} '{wtype}' '{wid}'"
        out.append(
            f"(button :class \"wall-item\" :onclick \"{onclick}\" "
            f"(box :class \"wall-item-inner\" :orientation \"v\" "
            f"(image :class \"wall-thumb\" :path \"{preview}\" :image-width 228 :image-height 128) "
            f"(label :class \"wall-name\" :text \"{name}\" :halign \"center\" :limit-width 200)))"
        )
    return out


def collect() -> tuple:
    static = []
    if STATIC_DIR.exists():
        for f in sorted(STATIC_DIR.iterdir()):
            if f.is_file() and f.suffix.lower() in IMG_EXTS:
                static.append({"type": "static", "id": str(f), "name": f.stem, "preview": str(f)})
    if GENRES_DIR.exists():
        for genre in sorted(p for p in GENRES_DIR.iterdir() if p.is_dir()):
            for f in sorted(genre.iterdir()):
                if f.is_file() and f.suffix.lower() in IMG_EXTS:
                    static.append({"type": "static", "id": str(f), "name": f.stem, "preview": str(f)})

    anim = []
    if ANIM_DIR.exists():
        for f in sorted(ANIM_DIR.glob("*.mp4")):
            thumb = Path.home() / f"Pictures/Wallpapers/.thumbs/animated_{f.stem}.png"
            anim.append({
                "type": "anim",
                "id": str(f),
                "name": f"▶ {f.stem}",
                "preview": str(thumb) if thumb.exists() else PLACEHOLDER,
            })

    we = []
    if WE_DIR.exists():
        for folder in sorted(WE_DIR.iterdir()):
            if not folder.is_dir():
                continue
            wfid = folder.name
            we.append({
                "type": "we",
                "id": wfid,
                "name": we_name(folder, wfid),
                "preview": we_preview(folder) or PLACEHOLDER,
            })
    return static, anim, we


def render_content(static, anim, we) -> str:
    blocks = []
    if anim:
        blocks.append(
            "(label :class \"wallpaper-section-title\" :text \"Animados\")"
            "(box :class \"wallpaper-list\" :orientation \"v\" :spacing 8 "
            + " ".join(build_items(anim)) + ")"
        )
    if static:
        blocks.append(
            "(label :class \"wallpaper-section-title\" :text \"Estáticos\")"
            "(box :class \"wallpaper-list\" :orientation \"v\" :spacing 8 "
            + " ".join(build_items(static)) + ")"
        )
    if we:
        blocks.append(
            "(label :class \"wallpaper-section-title\" :text \"Wallpaper Engine\")"
            "(box :class \"wallpaper-list\" :orientation \"v\" :spacing 8 "
            + " ".join(build_items(we)) + ")"
        )
    if not blocks:
        blocks.append("(label :class \"wallpaper-empty\" :text \"No hay fondos\")")
    return "(box :orientation \"v\" :spacing 10 " + "".join(blocks) + ")"


def main() -> None:
    static, anim, we = collect()
    content = render_content(static, anim, we)
    yuck = WINDOW_TEMPLATE.replace("__CONTENT__", content) + "\n"
    YUCK.write_text(yuck)
    sys.stdout.write("ok\n")


if __name__ == "__main__":
    main()