#!/bin/zsh

set -euo pipefail

alias_block='if [ -f ~/src/github.com/towase/dotfiles/alias.sh ]; then
    source ~/src/github.com/towase/dotfiles/alias.sh
fi'

touch ~/.zshrc

if ! grep -Fq "source ~/src/github.com/towase/dotfiles/alias.sh" ~/.zshrc; then
  {
    echo ""
    echo "${alias_block}"
  } >> ~/.zshrc
fi

# Set the number of rows and columns for the Dock
defaults write com.apple.dock springboard-rows -int 7
defaults write com.apple.dock springboard-columns -int 8
killall Dock
