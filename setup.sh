#!/bin/zsh

set -euo pipefail

ln -sf ~/src/github.com/towase/dotfiles/.gitconfig ~/.gitconfig

ln -sf ~/src/github.com/towase/dotfiles/.zshrc ~/.zshrc

# Set the number of rows and columns for the Dock
defaults write com.apple.dock springboard-rows -int 7
defaults write com.apple.dock springboard-columns -int 8

defaults write com.apple.dock autohide -bool true
defaults write com.apple.WindowManager EnableStandardClickToShowDesktop -bool false
defaults write com.apple.dock persistent-apps -array ""

killall Dock