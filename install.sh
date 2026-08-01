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

# 4) npm-only CLI exception via the repo-managed Node runtime
# takt is distributed via npm, isn't in aqua's standard registry, and Homebrew's tact is unrelated
mise x -- npm install -g takt@latest

# 5) chezmoi: manage dotfile symlinks
mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/chezmoi"
cat > "${XDG_CONFIG_HOME:-$HOME/.config}/chezmoi/chezmoi.toml" <<EOF
sourceDir = "${SCRIPT_DIR}"
EOF
chezmoi apply

# 6) self-updating CLI exception
command -v claude &>/dev/null || curl -fsSL https://claude.ai/install.sh | zsh
#command -v kiro-cli &>/dev/null || curl -fsSL https://cli.kiro.dev/install | bash

# 7) gcloud: self-updating SDK installed from the official tarball
#    (aqua/brew don't carry the component-managed SDK; kept current via `gcloud components update`.
#     PATH and shell completion are wired up in dot_zshrc, so install.sh skips rc-file edits.)
GCLOUD_SDK_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/google-cloud-sdk"
if ! command -v gcloud &>/dev/null && [[ ! -x "${GCLOUD_SDK_DIR}/bin/gcloud" ]]; then
  case "$(uname -sm)" in
    "Darwin arm64")  gcloud_archive="google-cloud-cli-darwin-arm.tar.gz" ;;
    "Darwin x86_64") gcloud_archive="google-cloud-cli-darwin-x86_64.tar.gz" ;;
    "Linux x86_64")  gcloud_archive="google-cloud-cli-linux-x86_64.tar.gz" ;;
    "Linux aarch64") gcloud_archive="google-cloud-cli-linux-arm.tar.gz" ;;
    *) echo "gcloud: unsupported platform: $(uname -sm)" >&2; exit 1 ;;
  esac
  mkdir -p "$(dirname "${GCLOUD_SDK_DIR}")"
  curl -fsSL "https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/${gcloud_archive}" \
    | tar -xz -C "$(dirname "${GCLOUD_SDK_DIR}")"
  "${GCLOUD_SDK_DIR}/install.sh" \
    --quiet \
    --usage-reporting=false \
    --path-update=false \
    --command-completion=false
fi
