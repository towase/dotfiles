---
name: kickoff
description: |
  GitHub issue を起点に作業を立ち上げる定型儀式を 1 コマンド化するスキル。
  issue 読解 → 論点潰し → status 更新 → ブランチ / worktree 準備 → workplan 作成 → 着手までを行う。
  「#123 を着手して」「この issue を進めて」「issue URL + 進めたい / worktree で着手して」と言及された際に使用する。
argument-hint: "<issue-url-or-number> [追加指示]"
user-invocable: true
---

# Kickoff - issue 着手の定型儀式

「issue URL + 進めて」の裏で毎回走っている立ち上げ手順を固定化する。リポジトリ固有の規約（ベースブランチ・PR 慣習・Projects 運用）は各リポジトリの CLAUDE.md / AGENTS.md と memory を正とし、このスキルは順序と抜け漏れ防止を担う。

## 手順

### 1. issue の読解

- issue 本文・全コメント・parent issue（sub issue の場合）・関連 PR を読む
- 達成条件（アウトカム）を自分の言葉で 1〜2 文に要約する。**要約できない issue は着手しない**（→ 手順 2 で論点として扱う）

```bash
gh issue view {番号} --json title,body,url,labels,assignees
gh api repos/{owner}/{repo}/issues/{番号}/comments --paginate --jq '.[] | {user: .user.login, body: .body[0:300]}'
```

### 2. 論点潰し（着手前）

- 仕様の曖昧さ・選択肢の分岐・スコープの不明点を洗い出す
- 論点があれば**実装に入る前に**ユーザーに確認する（提示方法はグローバルのコミュニケーションルールに従う）。「進めながら聞く」は、後戻りコストが小さいと判断できる場合のみ
- 論点がなければその旨を一言添えて先へ進む

### 3. issue status の更新

- リポジトリ / 組織で GitHub Projects 運用がある場合、issue の status を In Progress に更新し、必須フィールド（Team 等）が未設定なら設定する。運用の詳細は memory・リポジトリの規約に従う
- assignee が空なら自分（`gh api user --jq .login`）をアサインする

### 4. ブランチ / worktree の準備

- **ベースブランチをリポジトリの規約から確定させてから切る**（main とは限らない。デプロイ先とブランチの対応が memory / CLAUDE.md にあれば従う）
- ブランチ名は作業内容を反映（`feat/...`, `fix/...`）し、issue 番号を含める
- 並行作業がある場合や依頼に「worktree で」とある場合は worktree を作る。worktree 利用時は絶対パスの取り違え・.env 不在などの既知の落とし穴（memory 参照）に注意する

### 5. workplan の作成

- 作業が複数ステップ・複数 PR にまたがる見込みなら、workplan skill の規約に従って `~/.agents/workplans/<リポジトリ名>/<issue番号-トピック>.md` を作成する
- 1 PR で完結する小さな作業なら省略してよい

### 6. 着手

- 実装方針を 1〜3 行でユーザーに共有してから作業を開始する（承認待ちはしない。手順 2 で論点は潰済みのため）
- 以降は workplan の運用ルール（1 項目完了ごとに更新・確認を求めず続行）に従う
