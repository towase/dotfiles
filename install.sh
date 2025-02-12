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
)

for package in "${packages[@]}"; do
  brew install "$package"
done