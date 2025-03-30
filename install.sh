#!/bin/zsh

packages=(
  act
  awscli
  ffmpeg
  gh
  ghq
  imagemagick
  jq
  k1low/tap/runn
  lsd
  neovim
  suzuki-shunsuke/pinact/pinact
  tfenv
  tree
  trivy
  goodwithtech/r/dockle
  hstr
  zsh-completions
)

for package in "${packages[@]}"; do
  brew install "$package"
done

# to exec compinit for zsh-completions
chmod go-w '/opt/homebrew/share'