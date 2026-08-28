#!/usr/bin/env python3
"""Estetica y animacion compartidas por los desplegables de la barra.

Cada popup (volumen, brillo, monitor, spotify, sistema) traia su propio
bloque CSS con tonos distintos. Aqui vive la capa comun: se instala con
prioridad USER, por encima del CSS propio de cada script, asi que el
marco (fondo, borde, tipografia, sliders) queda identico en todos y cada
uno conserva solo sus reglas especificas de widget.

Uso:
    import popup_theme
    popup_theme.install()          # tras cargar el CSS propio
    popup_theme.prepare(win)       # antes de win.show_all()
    popup_theme.fade_in(win)       # despues de win.show_all()
"""
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk  # noqa: E402

# Paleta unica, la misma que la barra: velo morado claro y contorno
# morado oscuro. Los paneles van casi opacos a proposito: sin blur del
# compositor, texto y cifras sobre el wallpaper serian ilegibles.
BASE_CSS = b"""
window {
    background: linear-gradient(180deg, rgba(59, 44, 105, 0.97), rgba(28, 17, 56, 0.95));
    border: 1px solid rgba(109, 58, 192, 0.90);
    border-radius: 12px;
}

label { color: #f2ecff; font-size: 11px; }
label.title { color: #ffffff; font-size: 12px; font-weight: bold; }
label.key { color: #cfc4ea; }
label.val { color: #ffffff; font-weight: bold; }
label.hint { color: #b0a4d0; font-size: 10px; }

/* Sliders (volumen, brillo, progreso de spotify) */
scale trough {
    background-color: rgba(216, 180, 254, 0.18);
    border-radius: 999px;
    min-height: 5px;
}
scale highlight {
    background: linear-gradient(90deg, #8b5cf6, #d8b4fe);
    border-radius: 999px;
    min-height: 5px;
}
scale slider {
    background-color: #e4d9ff;
    border: none;
    border-radius: 999px;
    min-height: 12px;
    min-width: 12px;
    box-shadow: 0 0 8px rgba(139, 92, 246, 0.70);
}

/* Barras de nivel (estadisticas del sistema) */
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

scrollbar { background: transparent; }
scrollbar slider {
    background: rgba(216, 180, 254, 0.30);
    border-radius: 999px;
    min-height: 20px;
    min-width: 4px;
}
"""

# Animacion de apertura: desvanecido corto. Hyprland ya hace su
# "popin" al abrir la ventana; esto suaviza el borde duro del primer
# fotograma y da el mismo arranque a los cinco paneles.
FADE_MS = 150
FADE_STEP_MS = 10

_installed = [False]


def install(extra_css: bytes = b"") -> None:
    """Instala la capa comun por encima del CSS propio del script."""
    if _installed[0]:
        return
    _installed[0] = True
    provider = Gtk.CssProvider()
    provider.load_from_data(BASE_CSS + extra_css)
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), provider,
        Gtk.STYLE_PROVIDER_PRIORITY_USER,
    )


def prepare(win) -> None:
    """Deja la ventana transparente antes de mostrarla (evita el flash)."""
    try:
        win.set_opacity(0.0)
    except Exception:
        pass


def fade_in(win, duration_ms: int = FADE_MS) -> None:
    """Sube la opacidad de 0 a 1 con salida suave (ease-out cubica)."""
    steps = max(1, duration_ms // FADE_STEP_MS)
    state = {"i": 0}

    def tick() -> bool:
        state["i"] += 1
        t = min(1.0, state["i"] / steps)
        eased = 1 - (1 - t) ** 3
        try:
            win.set_opacity(eased)
        except Exception:
            return False
        return t < 1.0

    GLib.timeout_add(FADE_STEP_MS, tick)
