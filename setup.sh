#!/bin/zsh

echo '
if [ -f ~/src/github.com/stomy13/dotfiles/alias.sh ]; then
    source ~/src/github.com/stomy13/dotfiles/alias.sh
fi
' >> ~/.zshrc

# Set the number of rows and columns for the Dock
defaults write com.apple.dock springboard-rows -int 7
defaults write com.apple.dock springboard-columns -int 8
killall Dock