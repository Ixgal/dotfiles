#!/usr/bin/env python3
"""Compact wallpaper bar - tiny horizontal strip.

Generates eww.yuck with the wallpaper list as an eww variable (wm_items)
and a cursor variable (wm_sel) so the selection can move at runtime
with eww update (SUPER+X menu, arrows + Enter)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    HAS_GDK = True
except Exception:
    HAS_GDK = False

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wm_config import CELL_W, CELL_H, GAP, PAD, WINSIZE, CLOSE_W

WALLPAPER_DIRS = [Path.home() / "Pictures/Wallpapers"]
WE_WORKSHOP_DIR = Path.home() / ".local/share/Steam/steamapps/workshop/content/431960"
WE_DEFAULT_DIR = Path.home() / ".local/share/Steam/steamapps/common/wallpaper_engine/projects/defaultprojects"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".mkv"}
THUMB_DIR = Path.home() / ".cache/wallpaper-picker"
THUMB_SIZE = (160, 90)
STATE_FILE = Path.home() / ".config/eww/current_wallpaper"
SET_SCRIPT = "/home/jairo/.config/eww/scripts/set_wallpaper.sh"
NAV_SCRIPT = "/home/jairo/.config/eww/scripts/wallpaper_menu_nav.py"
TOGGLE_SCRIPT = "/home/jairo/.config/eww/scripts/toggle_wallpaper_menu.sh"
EWW_YUCK = Path.home() / ".config/eww/eww.yuck"


def thumb_path(key: str, stamp: str = "") -> Path:
    safe = key.replace("/", "_").replace(" ", "_")
    if stamp:
        safe = f"{safe}_{stamp}"
    return THUMB_DIR / f"{safe}.jpg"


def file_stamp(path: Path) -> str:
    """Huella barata del contenido (tamano+mtime): si un fondo se desinstala
    y se vuelve a instalar otro distinto con el mismo nombre, la miniatura
    no se reutiliza."""
    try:
        st = path.stat()
        return f"{st.st_size:x}-{st.st_mtime_ns:x}"
    except OSError:
        return ""


def make_thumbnail(src: Path, dst: Path) -> Path:
    if dst.exists():
        return dst
    dst.parent.mkdir(parents=True, exist_ok=True)
    if HAS_GDK:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(src), THUMB_SIZE[0], THUMB_SIZE[1], True
            )
            pixbuf.savev(str(dst), "jpeg", ["quality"], ["75"])
            return dst
        except Exception:
            pass
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-vf",
             f"scale={THUMB_SIZE[0]}:{THUMB_SIZE[1]}:force_original_aspect_ratio=decrease,"
             f"pad={THUMB_SIZE[0]}:{THUMB_SIZE[1]}:(ow-iw)/2:(oh-ih)/2",
             "-frames:v", "1", "-q:v", "5", str(dst)],
            capture_output=True, timeout=10
        )
        if dst.exists():
            return dst
    except Exception:
        pass
    return src


def collect_wallpapers() -> list[dict]:
    items = []
    seen = set()
    for base in WALLPAPER_DIRS:
        if not base.exists():
            continue
        for f in sorted(base.iterdir()):
            if f.is_file() and f.suffix.lower() in IMG_EXTS:
                key = str(f)
                if key in seen:
                    continue
                seen.add(key)
                t = thumb_path(f.stem, file_stamp(f))
                make_thumbnail(f, t)
                items.append({"type": "static", "path": str(f),
                              "thumb": str(t) if t.exists() else str(f)})
        genres_dir = base / "genres"
        if genres_dir.exists():
            for genre in sorted(p for p in genres_dir.iterdir() if p.is_dir()):
                for f in sorted(genre.iterdir()):
                    if f.is_file() and f.suffix.lower() in IMG_EXTS:
                        key = str(f)
                        if key in seen:
                            continue
                        seen.add(key)
                        t = thumb_path(f"{genre.name}_{f.stem}", file_stamp(f))
                        make_thumbnail(f, t)
                        items.append({"type": "static", "path": str(f),
                                      "thumb": str(t) if t.exists() else str(f)})
        anim_dir = base / "animados"
        if anim_dir.exists():
            for f in sorted(anim_dir.iterdir()):
                if f.is_file() and f.suffix.lower() in VIDEO_EXTS:
                    key = str(f)
                    if key in seen:
                        continue
                    seen.add(key)
                    t = thumb_path(f"anim_{f.stem}", file_stamp(f))
                    make_thumbnail(f, t)
                    items.append({"type": "anim", "path": str(f),
                                  "thumb": str(t) if t.exists() else str(SET_SCRIPT)})
    return items


def we_thumbnail(proj: Path, key: str) -> Path:
    for name in ("preview.jpg", "preview.jpeg", "preview.png", "preview.gif", "preview.webp"):
        src = proj / name
        if not src.is_file():
            continue
        dst = thumb_path(key, file_stamp(src))
        if dst.exists():
            return dst
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.suffix.lower() in (".jpg", ".jpeg"):
            try:
                shutil.copyfile(src, dst)
            except Exception:
                pass
        else:
            make_thumbnail(src, dst)
        return dst if dst.exists() else Path(SET_SCRIPT)
    return Path(SET_SCRIPT)


def project_usable(proj: Path) -> bool:
    """True si linux-wallpaperengine puede ejecutar el proyecto.

    El engine de Linux no soporta proyectos web ni .exe, y las escenas
    requieren "orthogonalprojection" con ancho en el scene file (si no,
    fallan al arrancar)."""
    try:
        meta = json.loads((proj / "project.json").read_text(encoding="utf-8",
                                                            errors="ignore"))
    except Exception:
        return False
    typ = str(meta.get("type", "") or "").lower()
    scene_file = str(meta.get("file", "") or "")
    if typ == "video":
        return True
    if typ == "web" or scene_file.lower().endswith((".html", ".htm", ".exe")):
        return False
    if (proj / "scene.pkg").exists():
        return True
    scene = proj / scene_file if scene_file else None
    if scene and scene.exists():
        try:
            sc = json.loads(scene.read_text(encoding="utf-8", errors="ignore"))
            op = sc.get("general", {}).get("orthogonalprojection")
            return isinstance(op, dict) and bool(op.get("width"))
        except Exception:
            return False
    return False


def collect_wallpaper_engine() -> list[dict]:
    items = []
    seen = set()
    for base, label in ((WE_WORKSHOP_DIR, "ws"), (WE_DEFAULT_DIR, "def")):
        if not base.exists():
            continue
        for proj in sorted(p for p in base.iterdir() if p.is_dir()):
            if not (proj / "scene.pkg").exists() and not (proj / "project.json").exists():
                continue
            if not project_usable(proj):
                continue
            key = str(proj)
            if key in seen:
                continue
            seen.add(key)
            t = we_thumbnail(proj, f"we_{label}_{proj.name}")
            items.append({"type": "we", "path": str(proj),
                          "thumb": str(t) if t.exists() else str(SET_SCRIPT)})
    return items


def cleanup_thumbs(items: list[dict]) -> None:
    """Borra miniaturas huerfanas (fondos desinstalados) de la cache."""
    if not THUMB_DIR.exists():
        return
    keep = set()
    for item in items:
        t = item.get("thumb", "")
        if t and str(Path(t).parent) == str(THUMB_DIR):
            keep.add(Path(t))
    for f in THUMB_DIR.iterdir():
        if f.suffix == ".jpg" and f not in keep:
            try:
                f.unlink()
            except OSError:
                pass


def esc_sh(s: str) -> str:
    return s.replace("'", "'\\''")


def build_yuck(items: list[dict]) -> str:
    entries = []
    for item in items:
        cmd = (f"{NAV_SCRIPT} click {item['type']} '{esc_sh(item['path'])}'")
        entries.append({
            "type": item["type"],
            "path": item["path"],
            "thumb": item["thumb"],
            "cmd": cmd,
        })
    items_json = json.dumps(entries, ensure_ascii=False).replace("\\", "\\\\").replace('"', '\\"')
    view0 = json.dumps(entries[:WINSIZE], ensure_ascii=False,
                       separators=(",", ":")).replace("\\", "\\\\").replace('"', '\\"')

    visible = min(len(entries), WINSIZE)
    total_w = visible * CELL_W + max(visible - 1, 0) * GAP + PAD * 2 + CLOSE_W
    total_h = CELL_H + PAD * 2 + 2

    return f"""(defvar wm_sel "")

(defvar wm_items "{items_json}")

(defvar wm_view "{view0}")

(defwindow wallpaper-menu
  :monitor 1
  :geometry (geometry
             :x "0px"
             :y "0px"
             :anchor "top right"
             :width "{total_w}px"
             :height "{total_h}px")
  :stacking "overlay"
  :windowtype "normal"
  :focusable "none"
  (box :class "wm" :orientation "h" :spacing {GAP}
    (for w in wm_view
      (button :class {{wm_sel == w.path ? "wc a" : "wc"}}
              :onclick "${{w.cmd}}"
        (overlay
          (image :path "${{w.thumb}}" :image-width {CELL_W - 6} :image-height {CELL_H - 6})
          (box :class "d" :halign "center" :valign "end" :visible {{wm_sel == w.path}} "●"))))
    (button :class "wx" :onclick "{TOGGLE_SCRIPT}" "✕")))
"""


def main():
    items = collect_wallpapers() + collect_wallpaper_engine()
    cleanup_thumbs(items)
    yuck = build_yuck(items)
    EWW_YUCK.parent.mkdir(parents=True, exist_ok=True)
    EWW_YUCK.write_text(yuck)
    print(f"Generated {len(items)} wallpapers")


if __name__ == "__main__":
    main()
