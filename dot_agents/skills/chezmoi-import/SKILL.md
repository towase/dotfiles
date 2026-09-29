---
name: chezmoi-import
description: chezmoi diff に現れる実環境の変更を dotfiles リポジトリへ取り込む。/chezmoi-import で呼び出す。
disable-model-invocation: true
---

# chezmoi-import

実環境 → chezmoi ソースの向きで変更を取り込む。

1. `chezmoi source-path` でソースを特定し、そのリポジトリの指示・`git status`・`git diff` と `chezmoi diff` を確認する。差分がなければ終了する。
2. `chezmoi diff` は実環境 → 管理内容への差分なので、表示をそのまま適用しない。対象ごとに `chezmoi source-path <実環境のパス>` を調べ、通常ファイルは `chezmoi add <実環境のパス>` で取り込む。テンプレート・include・シンボリックリンクは構造を保って対応するソースを編集する。既存の未コミット変更と衝突する場合や削除の意図が不明な場合は確認する。
3. `git diff`・`git diff --check`・`chezmoi diff` で取り込み内容と残差を確認し、変更と残差を短く報告する。

取り込み前に `chezmoi apply` で実環境を上書きしない。commit / push は別途依頼された場合のみ行う。
