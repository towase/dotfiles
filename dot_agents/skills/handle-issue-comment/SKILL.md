---
name: handle-issue-comment
description: 'GitHub issue コメントを起点に、その中の検討項目・選択肢・提案を構造化してユーザーと方針を固め、合意した内容を整理コメントとして issue に返す。トリガー例: "issues/123#issuecomment-456 について検討したい" / "〜のコメントの方針で実装を進めて" / "このコメントを整理して別コメントに返して" / "コメントの内容を整理したい"。GitHub issue コメントの URL や ID と一緒に「検討」「整理」「方針」「採否」「進めて」が登場したら使う。'
---

# Handle Issue Comment

GitHub issue のコメントには、複数の検討項目・選択肢・前提が混在していることが多い。このスキルは、そのコメントを起点に **方針を固めて整理コメントとして返す** までの定型フローを担当する。

## いつ使うか

ユーザーが以下のような形で指示してきたとき:

- `https://github.com/.../issues/123#issuecomment-456 について検討したい`
- `〜のコメントの phase 1 として実装を進めて`
- `このコメントを整理して別コメントに返して`
- `コメントに書かれた選択肢の採否を決めたい`

PR レビューコメント（`#discussion_rNNN`）は対象外 — そちらは `resolve-review-comments` / `review-resolve-loop` を使う。

## 手順

### 1. コメントを取得して内容を把握

URL からは `owner/repo` / `issue_number` / `comment_id` を抽出できる。

```bash
gh api repos/{owner}/{repo}/issues/comments/{comment_id} --jq '{user: .user.login, body: .body, html_url: .html_url, created_at: .created_at}'
```

issue 本文や前後コメントの文脈が必要そうなら追加で:

```bash
gh api repos/{owner}/{repo}/issues/{issue_number} --jq '{title, body, state}'
gh api repos/{owner}/{repo}/issues/{issue_number}/comments --jq '.[] | {user: .user.login, body: .body[0:200], created_at}'
```

### 2. コメント内容を構造化してユーザーに提示

コメントの中身を以下の枠で整理して、ユーザーに見せる:

- **前提・背景**: コメントが拠って立つ事実
- **検討項目**: 決めるべき論点（複数あれば箇条書き）
- **選択肢**: 各論点に対する選択肢と、AI から見た推奨
- **未確定の前提**: 確認が必要な項目

長いコメントなら全文の貼り直しは不要 — 構造化サマリで十分。

### 3. ユーザーに採否・優先度を確認

選択肢が複数ある場合は **1問ずつ** 確認する（`grill-me` の作法に近い）。一度に複数の論点を投げると、回答が漏れたり混乱しがち。

- 採用する選択肢
- フェーズ分け（phase 1 / phase 2 …）の有無と分け方
- 関連 issue の作成・close 判断

### 4. 合意した方針を「整理コメント」として整形

採用された方針を、**第三者が読んで実装に着手できる粒度** で整理する。

- 採用した結論を冒頭に書く（「〜の方針で進めます」）
- 検討経緯の要点（不採用案の却下理由を含める）
- スコープ（やること / やらないこと）
- フェーズ分けがあれば各フェーズの境界
- **how（実装詳細・ファイルパス・関数名）は書かない** — 既存メモリ `feedback_issue_no_how` と整合
- 既存メモリ `feedback_issue_team_beta` で求められる Team フィールド等は、新規 issue を作るときのみ気にする

### 5. 投稿

新しい整理コメントとして投稿:

```bash
gh api repos/{owner}/{repo}/issues/{issue_number}/comments \
  -X POST \
  -f body="$(cat <<'EOF'
〜の方針で進めます。

## 結論
...

## 検討の要点
...

## スコープ
...
EOF
)" \
  --jq '{html_url}'
```

投稿後、`html_url` をユーザーに報告して終わり。

## やらないこと

- 元コメントの編集（コメント主の意図を勝手に書き換えない）
- issue 本文の上書き（必要なら別タスクとして提案する）
- 同じターンでの実装着手 — 整理コメント投稿で一旦区切り、ユーザーから「実装を始めて」を受けてから着手する

## バリエーション

- **issue 本文に反映してほしい** と明示されたら、コメント投稿の代わりに `gh api repos/{owner}/{repo}/issues/{number} -X PATCH -f body=...` で本文更新
- **関連 PR に書くべき** 内容なら、`gh pr comment` で PR 側に投稿
- **新規 issue として切り出す** 必要があれば、`github-issues` skill に引き継ぐ
