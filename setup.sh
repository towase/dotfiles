#!/bin/zsh

set -euo pipefail

ln -sf ~/src/github.com/towase/dotfiles/.zshrc ~/.zshrc

# Set the number of rows and columns for the Dock
defaults write com.apple.dock springboard-rows -int 7
defaults write com.apple.dock springboard-columns -int 8
killall Dock
