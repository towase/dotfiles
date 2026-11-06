#!/usr/bin/env bash
# quiz-dir.sh が origin の形式ごとに同じ owner/repo/branch を返すことを確かめる
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export PR_QUIZ_DIR="$TMP/quiz" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
pass=0; fail=0
expect() { if [ "$2" = "$3" ]; then pass=$((pass+1)); echo "ok   - $1"; else fail=$((fail+1)); echo "FAIL - $1: expected [$2] got [$3]"; fi; }
mkrepo() { # $1 = dir, $2 = origin url (empty で無し)
  git init -q -b main "$1" && (cd "$1" && git config user.email t@e.com && git config user.name t && echo a > a && git add a && git commit -qm init && [ -z "$2" ] || git -C "$1" remote add origin "$2")
}
mkrepo "$TMP/ssh" git@github.com:acme/widget.git
mkrepo "$TMP/https" https://github.com/acme/widget.git
mkrepo "$TMP/sshurl" ssh://git@github.com/acme/widget
mkrepo "$TMP/noremote" ""
expect "ssh origin" "$PR_QUIZ_DIR/acme/widget/main" "$(cd "$TMP/ssh" && bash "$SCRIPT_DIR/quiz-dir.sh")"
expect "https origin" "$PR_QUIZ_DIR/acme/widget/main" "$(cd "$TMP/https" && bash "$SCRIPT_DIR/quiz-dir.sh")"
expect "ssh:// origin" "$PR_QUIZ_DIR/acme/widget/main" "$(cd "$TMP/sshurl" && bash "$SCRIPT_DIR/quiz-dir.sh")"
expect "no origin uses dir name" "$PR_QUIZ_DIR/noremote/main" "$(cd "$TMP/noremote" && bash "$SCRIPT_DIR/quiz-dir.sh")"
(cd "$TMP/ssh" && git checkout -qb feat/x)
expect "branch slash becomes __" "$PR_QUIZ_DIR/acme/widget/feat__x" "$(cd "$TMP/ssh" && bash "$SCRIPT_DIR/quiz-dir.sh")"
expect "directory is created" "yes" "$([ -d "$PR_QUIZ_DIR/acme/widget/feat__x" ] && echo yes || echo no)"
(cd "$TMP" && bash "$SCRIPT_DIR/quiz-dir.sh" >/dev/null 2>&1); expect "outside git repo exits 1" 1 "$?"
echo; echo "passed=$pass failed=$fail"; [ "$fail" -eq 0 ]
