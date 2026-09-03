#!/bin/bash
set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[*]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
err()   { echo -e "${RED}[✗]${NC} $1"; }

backup_and_link() {
    local src="$1" dst="$2"
    mkdir -p "$(dirname "$dst")"
    if [ -L "$dst" ]; then
        rm "$dst"
    elif [ -e "$dst" ]; then
        warn "Backup: $dst -> ${dst}.bak"
        mv "$dst" "${dst}.bak"
    fi
    ln -sf "$src" "$dst"
}

# ─── 1. Instalar paquetes ───────────────────────────────────────────
install_packages() {
    info "Instalando paquetes de pacman..."
    if [ -f "$DOTFILES_DIR/pacman-pkgs.txt" ]; then
        sudo pacman -S --needed --noconfirm - < "$DOTFILES_DIR/pacman-pkgs.txt"
        ok "Pacman: $(wc -l < "$DOTFILES_DIR/pacman-pkgs.txt") paquetes"
    fi

    # Paquetes opcionales de GPU (solo se instalan si existen en los repos)
    if [ -f "$DOTFILES_DIR/gpu-pkgs.txt" ]; then
        while IFS= read -r pkg; do
            [ -z "$pkg" ] && continue
            if pacman -Si "$pkg" >/dev/null 2>&1; then
                sudo pacman -S --needed --noconfirm "$pkg" 2>/dev/null || warn "No se pudo instalar: $pkg"
            else
                warn "Saltando $pkg (no disponible en esta máquina)"
            fi
        done < "$DOTFILES_DIR/gpu-pkgs.txt"
    fi

    # Instalar yay si no existe
    if ! command -v yay &>/dev/null; then
        info "Instalando yay..."
        git clone https://aur.archlinux.org/yay-bin.git /tmp/yay-bin
        (cd /tmp/yay-bin && makepkg -si --noconfirm)
        rm -rf /tmp/yay-bin
        ok "yay instalado"
    fi

    info "Instalando paquetes AUR..."
    if [ -f "$DOTFILES_DIR/aur-pkgs.txt" ]; then
        yay -S --needed --noconfirm - < "$DOTFILES_DIR/aur-pkgs.txt"
        ok "AUR: $(wc -l < "$DOTFILES_DIR/aur-pkgs.txt") paquetes"
    fi

    info "Instalando Flatpaks..."
    if [ -f "$DOTFILES_DIR/flatpak-pkgs.txt" ] && [ -s "$DOTFILES_DIR/flatpak-pkgs.txt" ]; then
        flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
        while IFS= read -r app; do
            [ -z "$app" ] && continue
            flatpak install -y flathub "$app" 2>/dev/null || warn "No se pudo instalar: $app"
        done < "$DOTFILES_DIR/flatpak-pkgs.txt"
        ok "Flatpaks instalados"
    fi
}

# ─── 2. Vincular dotfiles ───────────────────────────────────────────
link_dotfiles() {
    info "Vinculando dotfiles..."

    # Shell
    backup_and_link "$DOTFILES_DIR/bash/.bashrc"       "$HOME/.bashrc"
    backup_and_link "$DOTFILES_DIR/bash/.bash_profile"  "$HOME/.bash_profile"
    backup_and_link "$DOTFILES_DIR/bash/.bash_logout"   "$HOME/.bash_logout"

    # Zsh
    backup_and_link "$DOTFILES_DIR/zsh/.zshrc"    "$HOME/.zshrc"
    backup_and_link "$DOTFILES_DIR/zsh/.profile"  "$HOME/.profile"

    # Git
    backup_and_link "$DOTFILES_DIR/git/.gitconfig" "$HOME/.gitconfig"

    # Fish
    [ -d "$DOTFILES_DIR/fish" ] && \
        backup_and_link "$DOTFILES_DIR/fish" "$HOME/.config/fish"

    # Dunst
    [ -d "$DOTFILES_DIR/dunst" ] && \
        backup_and_link "$DOTFILES_DIR/dunst" "$HOME/.config/dunst"

    # XDG (archivos sueltos de ~/.config)
    if [ -d "$DOTFILES_DIR/xdg" ]; then
        for file in "$DOTFILES_DIR/xdg"/*; do
            [ -f "$file" ] || continue
            backup_and_link "$file" "$HOME/.config/$(basename "$file")"
        done
    fi

    # lean-ctx
    backup_and_link "$DOTFILES_DIR/lean-ctx/layout.toml" "$HOME/.config/lean-ctx/layout.toml"

    # Hyprland
    backup_and_link "$DOTFILES_DIR/hypr/hyprland.conf"  "$HOME/.config/hypr/hyprland.conf"
    backup_and_link "$DOTFILES_DIR/hypr/hyprpaper.conf" "$HOME/.config/hypr/hyprpaper.conf"

    # Hyprland lua config
    backup_and_link "$DOTFILES_DIR/hypr/hyprland.lua" "$HOME/.config/hypr/hyprland.lua"

    # Wallpapers
    if [ -d "$DOTFILES_DIR/wallpapers" ]; then
        mkdir -p "$HOME/Pictures/Wallpapers"
        cp -rn "$DOTFILES_DIR/wallpapers/"* "$HOME/Pictures/Wallpapers/" 2>/dev/null || true
    fi

    # Fuentes
    if [ -d "$DOTFILES_DIR/fonts" ]; then
        mkdir -p "$HOME/.local/share/fonts"
        cp -n "$DOTFILES_DIR/fonts/"* "$HOME/.local/share/fonts/" 2>/dev/null || true
        fc-cache -f "$HOME/.local/share/fonts" 2>/dev/null || true
    fi

    # Cursores
    if [ -d "$DOTFILES_DIR/icons" ]; then
        mkdir -p "$HOME/.local/share/icons"
        for cursor in "$DOTFILES_DIR/icons/"*; do
            [ -d "$cursor" ] && cp -rn "$cursor" "$HOME/.local/share/icons/" 2>/dev/null || true
        done
    fi

    # Kitty
    mkdir -p "$HOME/.config/kitty"
    backup_and_link "$DOTFILES_DIR/kitty/kitty.conf" "$HOME/.config/kitty/kitty.conf"
    [ -f "$DOTFILES_DIR/kitty/violet-nacarado.png" ] && \
        cp -n "$DOTFILES_DIR/kitty/violet-nacarado.png" "$HOME/.config/kitty/" 2>/dev/null || true

    # Eww
    backup_and_link "$DOTFILES_DIR/eww" "$HOME/.config/eww"

    # OpenCode
    backup_and_link "$DOTFILES_DIR/opencode/opencode.jsonc" "$HOME/.config/opencode/opencode.jsonc"
    backup_and_link "$DOTFILES_DIR/opencode/tui.json"       "$HOME/.config/opencode/tui.json"
    backup_and_link "$DOTFILES_DIR/opencode/themes"         "$HOME/.config/opencode/themes"
    backup_and_link "$DOTFILES_DIR/opencode/opencode-home.json" "$HOME/opencode.json"

    # Waybar
    [ -d "$DOTFILES_DIR/waybar" ] && \
        backup_and_link "$DOTFILES_DIR/waybar" "$HOME/.config/waybar"

    # Rofi
    [ -d "$DOTFILES_DIR/rofi" ] && \
        backup_and_link "$DOTFILES_DIR/rofi" "$HOME/.config/rofi"

    # Wofi
    [ -d "$DOTFILES_DIR/wofi" ] && \
        backup_and_link "$DOTFILES_DIR/wofi" "$HOME/.config/wofi"

    # nwg-dock
    [ -d "$DOTFILES_DIR/nwg-dock-hyprland" ] && \
        backup_and_link "$DOTFILES_DIR/nwg-dock-hyprland" "$HOME/.config/nwg-dock-hyprland"

    # nwg-drawer
    [ -d "$DOTFILES_DIR/nwg-drawer" ] && \
        backup_and_link "$DOTFILES_DIR/nwg-drawer" "$HOME/.config/nwg-drawer"

    # GTK
    [ -d "$DOTFILES_DIR/gtk-3.0" ] && \
        backup_and_link "$DOTFILES_DIR/gtk-3.0" "$HOME/.config/gtk-3.0"
    [ -d "$DOTFILES_DIR/gtk-4.0" ] && \
        backup_and_link "$DOTFILES_DIR/gtk-4.0" "$HOME/.config/gtk-4.0"

    # Systemd user services
    [ -d "$DOTFILES_DIR/systemd/user" ] && \
        backup_and_link "$DOTFILES_DIR/systemd/user" "$HOME/.config/systemd/user"

    ok "Dotfiles vinculados"
}

# ─── 3. Copiar scripts a ~/.local/bin/ ──────────────────────────────
install_scripts() {
    info "Instalando scripts personales..."
    mkdir -p "$HOME/.local/bin"

    if [ -d "$DOTFILES_DIR/local-bin" ]; then
        for script in "$DOTFILES_DIR/local-bin"/*; do
            [ -f "$script" ] || continue
            cp -f "$script" "$HOME/.local/bin/"
            chmod +x "$HOME/.local/bin/$(basename "$script")"
        done
        ok "Scripts copiados: $(ls "$DOTFILES_DIR/local-bin" | wc -l) archivos"
    fi

    # Asegurar que ~/.local/bin está en PATH
    if ! grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        ok "PATH actualizado en .bashrc"
    fi
}

# ─── 4. Habilitar servicios ─────────────────────────────────────────
enable_services() {
    info "Habilitando servicios systemd..."
    local services=(
        "bluez-auto-trust.service"
    )
    for svc in "${services[@]}"; do
        if [ -f "$HOME/.config/systemd/user/$svc" ] || \
           [ -f "$DOTFILES_DIR/systemd/user/$svc" ]; then
            systemctl --user enable "$svc" 2>/dev/null && ok "$svc habilitado" || warn "No se pudo habilitar $svc"
        fi
    done
}

# ─── 5. Configurar locale y teclado ─────────────────────────────────
setup_locale() {
    info "Configurando locale y teclado..."
    sudo localectl set-keymap es 2>/dev/null || true
    sudo localectl set-x11-keymap es 2>/dev/null || true

    if ! grep -q 'es_ES.UTF-8' /etc/locale.gen 2>/dev/null; then
        sudo sed -i 's/#es_ES.UTF-8/es_ES.UTF-8/' /etc/locale.gen
        sudo locale-gen 2>/dev/null || true
    fi
    ok "Locale configurado"
}

# ─── 5b. Restaurar ajustes dconf (colores, tema, etc) ──────────────
apply_dconf() {
    if [ -f "$DOTFILES_DIR/dconf/settings.ini" ]; then
        info "Restaurando ajustes dconf..."
        dconf load / < "$DOTFILES_DIR/dconf/settings.ini" 2>/dev/null || warn "No se pudo aplicar dconf"
        ok "dconf restaurado"
    fi
}

# ─── 6. Copiar archivos de configuración del sistema ────────────────
install_system_configs() {
    info "Copiando configs del sistema (si existen)..."
    [ -f "$DOTFILES_DIR/etc/pacman.conf" ] && \
        sudo cp "$DOTFILES_DIR/etc/pacman.conf" /etc/pacman.conf
    [ -f "$DOTFILES_DIR/etc/makepkg.conf" ] && \
        sudo cp "$DOTFILES_DIR/etc/makepkg.conf" /etc/makepkg.conf

    # Tema SDDM "nebula"
    if [ -d "$DOTFILES_DIR/sddm/nebula" ]; then
        info "Instalando tema SDDM 'nebula'..."
        sudo mkdir -p /usr/share/sddm/themes/nebula
        sudo cp -r "$DOTFILES_DIR/sddm/nebula/." /usr/share/sddm/themes/nebula/
        sudo mkdir -p /etc/sddm.conf.d
        sudo tee /etc/sddm.conf.d/10-nebula.conf >/dev/null <<EOF
[Theme]
Current=nebula
EOF
        ok "Tema SDDM instalado y activado"
    fi

    ok "Configs del sistema procesadas"
}

# ─── Menú principal ─────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║   Dotfiles Installer - Ixgal        ║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
    echo ""

    case "${1:-all}" in
        --packages|-p)  install_packages ;;
        --link|-l)      link_dotfiles ;;
        --scripts|-s)   install_scripts ;;
        --services)     enable_services ;;
        --locale)       setup_locale ;;
        --system|-c)    install_system_configs ;;
        --export|-e)
            info "Exportando listas de paquetes..."
            comm -23 <(pacman -Qqe | sort) <(pacman -Qqm | sort) > "$DOTFILES_DIR/pacman-pkgs.txt"
            pacman -Qqm > "$DOTFILES_DIR/aur-pkgs.txt"
            pacman -Qe > "$DOTFILES_DIR/all-pkgs.txt"
            flatpak list --app --columns=application 2>/dev/null | sort > "$DOTFILES_DIR/flatpak-pkgs.txt"
            ok "Listas exportadas a $DOTFILES_DIR/"
            ok "  pacman-pkgs.txt  ($(wc -l < "$DOTFILES_DIR/pacman-pkgs.txt") paquetes)"
            ok "  aur-pkgs.txt     ($(wc -l < "$DOTFILES_DIR/aur-pkgs.txt") paquetes)"
            ok "  flatpak-pkgs.txt ($(wc -l < "$DOTFILES_DIR/flatpak-pkgs.txt") flatpaks)"
            ;;
        all)
            link_dotfiles
            install_scripts
            setup_locale
            apply_dconf
            enable_services
            install_system_configs
            echo ""
            ok "¡Dotfiles instalados!"
            echo ""
            warn "Para instalar paquetes ejecuta:"
            echo "  $0 --packages"
            warn "Para re-exportar paquetes desde este PC:"
            echo "  $0 --export"
            ;;
        *)
            echo "Uso: $0 [opción]"
            echo ""
            echo "  Sin args    Instalar todo (sin paquetes)"
            echo "  --packages  Instalar paquetes pacman + AUR + Flatpak"
            echo "  --link      Vincular dotfiles"
            echo "  --scripts   Copiar scripts a ~/.local/bin/"
            echo "  --services  Habilitar servicios systemd"
            echo "  --locale    Configurar locale y teclado"
            echo "  --system    Copiar configs del sistema (/etc) + tema SDDM"
            echo "  --export    Exportar listas de paquetes actuales"
            echo "  --all       Todo lo anterior"
            exit 1
            ;;
    esac
}

main "$@"
