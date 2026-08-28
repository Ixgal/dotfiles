#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '

# Scripts propios (~/.local/bin)
export PATH="$HOME/.local/bin:$PATH"
export LOCPATH=/home/jairo/.locales

. "$HOME/.local/share/../bin/env"

# Herramientas IA (ahorro de tokens): lean-ctx, codegraph, cavemem, uv/serena, rtk
export PATH="$HOME/.npm-global/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
# >>> lean-ctx wrap claude >>>
export ANTHROPIC_BASE_URL="http://127.0.0.1:4444"
# <<< lean-ctx wrap claude <<<
