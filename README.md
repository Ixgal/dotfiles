# Dotfiles

Configuraciones personales para:
- **Shell**: bash, zsh, fish
- **Hyprland**: configuración del compositor Wayland + hyprpaper
- **Kitty**: terminal
- **Waybar**: barra + dock (popups, tema nacarado)
- **Eww**: widgets del escritorio
- **Rofi / Wofi / nwg-dock / nwg-drawer**: launchers y dock
- **OpenCode**: configuración + temas
- **GTK / dconf**: tema oscuro, colores del sistema, cursor Posys
- **Fonts**: Symbols Nerd Font
- **Wallpapers**
- **SDDM**: tema nebula
- **Systemd**: servicios de usuario
- **Scripts**: `~/.local/bin/`
- **Pacman**: `/etc/pacman.conf` (Color, ParallelDownloads)

## Uso

```bash
git clone https://github.com/Ixgal/dotfiles.git ~/dotfiles
cd ~/dotfiles
chmod +x install.sh
./install.sh            # vincula configs, scripts, locale, dconf, servicios, SDDM
./install.sh --packages # instala paquetes pacman + AUR + flatpak
```

## Exportar paquetes desde este PC

```bash
./install.sh --export
```
