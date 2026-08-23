#!/bin/bash

DOTFILES_DIR="$(cd "$(dirname "$0")" && pwd)"

ln -sf "$DOTFILES_DIR/bash/.bashrc" "$HOME/.bashrc"
ln -sf "$DOTFILES_DIR/bash/.bash_profile" "$HOME/.bash_profile"
ln -sf "$DOTFILES_DIR/bash/.bash_logout" "$HOME/.bash_logout"

ln -sf "$DOTFILES_DIR/hypr/hyprland.conf" "$HOME/.config/hypr/hyprland.conf"
ln -sf "$DOTFILES_DIR/hypr/hyprpaper.conf" "$HOME/.config/hypr/hyprpaper.conf"

ln -sf "$DOTFILES_DIR/kitty/kitty.conf" "$HOME/.config/kitty/kitty.conf"

ln -sf "$DOTFILES_DIR/eww" "$HOME/.config/eww"

ln -sf "$DOTFILES_DIR/opencode/opencode.jsonc" "$HOME/.config/opencode/opencode.jsonc"
ln -sf "$DOTFILES_DIR/opencode/tui.json" "$HOME/.config/opencode/tui.json"

echo "Dotfiles vinculados correctamente!"
