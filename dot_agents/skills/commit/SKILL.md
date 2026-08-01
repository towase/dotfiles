---
name: commit
description: 現在の作業ツリーの変更を、CLAUDE.md の commit ルール（Conventional Commits 風プレフィックス + Co-Authored-By 行 + HEREDOC 渡し）に従って即 commit する。呼び出された時点で commit 作成の承認とみなし、メッセージの事前ドラフト確認はスキップする。「/commit」と明示的に指示されたとき、または本 skill が呼び出されたときに使用する。
disable-model-invocation: true
allowed-tools: Bash, Read
---

# commit

呼び出された瞬間に、現在の git 差分を 1 つの commit にまとめる。skill 起動 = commit 作成の承認とみなすため、メッセージドラフトを事前提示してユーザーの OK を待たない。

## 前提

- CLAUDE.md の「commit は明示依頼時のみ」のルールは、この skill の呼び出し自体を明示依頼として満たす。
- main / master への直接コミットの可否は、本リポジトリのプロジェクトルール、および [[work-on-main]] skill の有効/無効に従う。新しいフィーチャーブランチを切る責務はこの skill にはない（必要なら呼び出し前に切っておくこと）。

## 手順

### 1. 現状を並列で取得

以下を Bash で並列実行する:

```sh
git status
git diff
git log --oneline -n 5
```

- `.env` / `credentials*.json` / 秘密鍵らしき内容を含むファイルが差分にある場合は、commit に進まずユーザーに確認する。
- バイナリや巨大な生成物が紛れていれば、それも確認対象にする。

### 2. commit メッセージを起草

- Conventional Commits 風プレフィックス（`feat:` / `fix:` / `docs:` / `chore:` / `refactor:` / `test:` 等）を使う。
- 1 行目は 70 文字以内のサマリ。
- 必要に応じて本文に 1〜2 文の why を書く。「何をしたか」は diff で読めるので繰り返さない。
- 末尾に空行 + `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` を必ず付ける（モデル名は実行時のモデル表記に合わせる）。

### 3. 関連ファイルだけを add

- `git add .` / `git add -A` は使わない。
- 直前の `git status` / `git diff` で挙がっていたファイルだけを個別パス指定で add する。
- 想定外のファイル（自動生成物、他人の作業ファイル等）が紛れていれば確認する。

### 4. HEREDOC で commit を作成

```sh
git commit -m "$(cat <<'EOF'
<type>: <one-line summary>

<optional why, 1-2 sentences>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- `--no-verify` / `--no-gpg-sign` / `--amend` は使わない。
- pre-commit hook が失敗したら commit は作成されていない。内容を修正して **新しい** commit を作る（前の commit を amend しない）。

### 5. 確認

commit 後に `git status` を流し、ツリーがクリーンになったか・短い HEAD SHA を 1 行で報告する。

## やらないこと

- commit メッセージの事前ドラフト提示と承認待ち
- push（push したいときは [[push]] または [[commit-and-push]] を使う）
- `git add .` / `git add -A`
- `--amend` / `--no-verify` / `--no-gpg-sign`
- 新しいブランチの作成
