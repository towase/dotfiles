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

# 2) aqua: CLI packages
aqua install
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/aquaproj-aqua"
ln -sf "${SCRIPT_DIR}/aqua.yaml" "${XDG_CONFIG_HOME:-$HOME/.config}/aquaproj-aqua/aqua.yaml"


# 3) mise: runtime versions
mise trust -y "${SCRIPT_DIR}/mise.toml"
mise install

# 4) self-updating CLI exception
curl -fsSL https://claude.ai/install.sh | zsh
