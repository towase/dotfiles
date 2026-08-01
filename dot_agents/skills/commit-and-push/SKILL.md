---
name: commit-and-push
description: 現在の作業ツリーの変更を [[commit]] と同じ手順で commit し、続けて [[push]] と同じ手順で origin に push する。commit に失敗したら push しない。push に失敗しても commit は残す。「/commit-and-push」と明示的に指示されたとき、または本 skill が呼び出されたときに使用する。
disable-model-invocation: true
allowed-tools: Bash, Read
---

# commit-and-push

呼び出された瞬間に、現在の差分を 1 つの commit にまとめてから、現在のブランチを `origin` に push する。

## 前提

- skill の呼び出し自体を commit / push の明示依頼とみなす。メッセージドラフトの事前承認は取らない。
- main / master への直接 push の可否は、本リポジトリのプロジェクトルールおよび [[work-on-main]] の有効/無効に従う。

## 手順

### 1. commit

#### 1-1. 現状を並列で取得

```sh
git status
git diff
git log --oneline -n 5
```

- `.env` / `credentials*.json` / 秘密鍵らしきファイルが含まれていれば、ここで止めて確認する。

#### 1-2. メッセージ起草

- Conventional Commits 風プレフィックス（`feat:` / `fix:` / `docs:` / `chore:` / `refactor:` / `test:` 等）。
- 1 行目は 70 文字以内のサマリ。
- 必要に応じて本文に 1〜2 文の why。「何をしたか」は diff で読めるので書かない。
- 末尾に空行 + `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>`（モデル名は実行時のモデルに合わせる）。

#### 1-3. add & commit

```sh
git add <changed-paths>...
git commit -m "$(cat <<'EOF'
<type>: <summary>

<optional why>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

- `git add .` / `git add -A` は使わない。
- `--amend` / `--no-verify` / `--no-gpg-sign` は使わない。
- pre-commit hook が失敗した場合は、commit は作成されていない。内容を修正して **新しい** commit を作る。
- ここで失敗したら **push に進まない**。失敗状態を報告して終了する。

### 2. push

#### 2-1. 上流確認

```sh
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

#### 2-2. push 実行

- 上流あり: `git push`
- 上流なし: `git push -u origin <current-branch>`
- force push（`--force` / `--force-with-lease`）はこの skill では実行しない。

### 3. 確認

```sh
git status
```

commit 後の短い HEAD SHA と push 先のリモートブランチ名を 1 行で報告する。

## 失敗時の挙動

- **commit に失敗**: push に進まない。失敗内容と現在の状態を報告して終了する。
- **push に失敗（commit は成功）**: commit はロールバックせずそのまま残す。push 失敗の原因（拒否 / ネットワーク / 上流未設定など）と次のアクション候補を報告する。

## やらないこと

- commit メッセージの事前ドラフト提示と承認待ち
- `git add .` / `git add -A`
- `--amend` / `--no-verify` / `--no-gpg-sign` / force push
- 新しいリモート・新しいブランチの作成
- push 後の CI 結果の監視
