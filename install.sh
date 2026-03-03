#!/bin/zsh

packages=(
  act
  awscli
  ffmpeg
  exiftool
  gh
  ghq
  imagemagick
  jq
  k1low/tap/runn
  lazygit
  lsd
  neovim
  ni
  suzuki-shunsuke/pinact/pinact
  ripgrep
  tfenv
  tree
  trivy
  goodwithtech/r/dockle
  hstr
  volta
  zsh-completions
)

for package in "${packages[@]}"; do
  brew install "$package"
done

# to exec compinit for zsh-completions
chmod go-w '/opt/homebrew/share'

volta install node