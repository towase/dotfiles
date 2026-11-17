#!/usr/bin/env bash
# 現在のブランチのクイズ記録ディレクトリ（~/.agents/pr-quiz/<owner>/<repo>/<branch>/）を作って表示する。
# 出題と回答をここに残すのは、後から復習できるようにするため。根は PR_QUIZ_DIR で変えられる。
set -euo pipefail

root="${PR_QUIZ_DIR:-$HOME/.agents/pr-quiz}"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "git リポジトリの中で実行してください" >&2; exit 1; }

# origin の URL のパス部分（owner/repo）。ユーザー名・トークン・ホスト・ポートは記録先のパスに残さない
repo_key() {
  local u path part out=""
  local -a parts
  u="$(printf '%s' "$1" | sed -E 's#/+$##; s#\.git$##')"
  if [[ "$u" =~ ^[A-Za-z][A-Za-z0-9+.-]*:// ]]; then
    path="${u#*://}"
    if [[ "$path" == */* ]]; then path="${path#*/}"; else path=""; fi
  elif [[ "$u" =~ ^[^/]+: ]]; then
    path="${u#*:}" # scp 形式（[user@]host:path）
  else
    path="$u" # ローカルパス
  fi
  # 空・.・.. の要素を落とし、記録先の外を指さないようにする
  IFS=/ read -r -a parts <<<"$path"
  for part in ${parts[@]+"${parts[@]}"}; do
    case "$part" in '' | . | ..) continue ;; esac
    out="${out:+${out}/}${part}"
  done
  printf '%s' "$out"
}

# origin が無いか、パスを取り出せなければトップレベルのディレクトリ名
url="$(git remote get-url origin 2>/dev/null || true)"
key=""
[ -n "$url" ] && key="$(repo_key "$url")"
[ -n "$key" ] || key="$(basename "$(git rev-parse --show-toplevel)")"
branch="$(git rev-parse --abbrev-ref HEAD)"
dir="${root}/${key}/${branch//\//__}"
mkdir -p "$dir"
printf '%s\n' "$dir"
