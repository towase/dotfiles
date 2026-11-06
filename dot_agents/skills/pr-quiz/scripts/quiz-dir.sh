#!/usr/bin/env bash
# 現在のブランチのクイズ記録ディレクトリ（~/.agents/pr-quiz/<owner>/<repo>/<branch>/）を作って表示する。
# 出題と回答をここに残すのは、後から復習できるようにするため。根は PR_QUIZ_DIR で変えられる。
set -euo pipefail

root="${PR_QUIZ_DIR:-$HOME/.agents/pr-quiz}"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "git リポジトリの中で実行してください" >&2; exit 1; }

# origin の owner/repo。無ければトップレベルのディレクトリ名
url="$(git remote get-url origin 2>/dev/null || true)"
if [ -n "$url" ]; then
  key="$(printf '%s' "$url" | sed -E 's#^(ssh://)?[^@/]*@##; s#^https?://##; s#^[^/:]*[:/]##; s#\.git$##; s#/+$##')"
else
  key="$(basename "$(git rev-parse --show-toplevel)")"
fi
branch="$(git rev-parse --abbrev-ref HEAD)"
dir="${root}/${key}/${branch//\//__}"
mkdir -p "$dir"
printf '%s\n' "$dir"
