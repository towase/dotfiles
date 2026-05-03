#!/bin/zsh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}"

# 1) brew: OS packages and exceptions
brew bundle --file "${SCRIPT_DIR}/Brewfile"

# to exec compinit for zsh-completions
if [[ -d /opt/homebrew/share ]]; then
  chmod go-w '/opt/homebrew/share'
fi

# 2) aqua: CLI packages (includes chezmoi)
aqua install
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/aquaproj-aqua"
ln -sf "${SCRIPT_DIR}/aqua.yaml" "${XDG_CONFIG_HOME:-$HOME/.config}/aquaproj-aqua/aqua.yaml"

# 3) mise: runtime versions
mise trust -y "${SCRIPT_DIR}/mise.toml"
mise install

# 4) chezmoi: manage dotfile symlinks
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/chezmoi"
cat > "${XDG_CONFIG_HOME:-$HOME/.config}/chezmoi/chezmoi.toml" <<EOF
sourceDir = "${SCRIPT_DIR}"
EOF
chezmoi apply

# 5) self-updating CLI exception
command -v claude &>/dev/null || curl -fsSL https://claude.ai/install.sh | zsh
command -v kiro-cli &>/dev/null || curl -fsSL https://cli.kiro.dev/install | bash
