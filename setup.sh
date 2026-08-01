#!/bin/zsh

set -euo pipefail

# Dockの行数と列数を設定する
defaults write com.apple.dock springboard-rows -int 7
defaults write com.apple.dock springboard-columns -int 8

# Dockを自動的に表示・非表示にする
defaults write com.apple.dock autohide -bool true
# デスクトップをクリックしてもウィンドウを表示しない
defaults write com.apple.WindowManager EnableStandardClickToShowDesktop -bool false

killall Dock
