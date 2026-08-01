---
name: workplan
description: |
  複数ステップ・複数セッションにまたがる作業の外部状態ファイル（workplan）を作成・更新・再開するスキル。
  done / in-progress / next / blocked を markdown 1 枚で管理し、セッションを跨いでランを積み上げる。
  「workplan を作って」「作業キューを作って」「続きから再開して」「今どこまで進んでる？」と言及された際、
  または epic・複数 PR にまたがる作業に着手する際に使用する。
argument-hint: "[create|resume|status] [トピック]"
user-invocable: true
---

# Workplan - 作業キューの外部状態ファイル

「次へ」「続けて」をユーザーに打たせないための仕組み。作業の状態をコンテキストではなくファイルに持たせ、セッションが変わっても・compact されても、workplan を読めば続きから再開できるようにする。

## ファイル規約

- **パス**: `~/.agents/workplans/<リポジトリ名>/<トピック>.md`
  - リポジトリ名は `git remote get-url origin` の `owner-repo` 形式（例: `example-org-example-project`）。リポジトリ外の作業は `general`
  - トピックは epic の issue 番号かケバブケースの短い名前（例: `15935-e2b-template-versioning`）
- **リポジトリ内には置かない**: PR の差分を汚染するため
- **フォーマット**:

```markdown
# <トピック名>

<背景 1〜3 行。関連 issue / PR の URL>

## in-progress

- [ ] <今やっている 1 項目。着手時に next から移す>

## next

- [ ] <次にやる項目。上から順に取る>
- [ ] ...

## blocked

- [ ] <項目> — 待ち理由（例: PR #123 のレビュー待ち。Monitor 登録済み）

## done

- [x] <完了した項目> (YYYY-MM-DD, PR #123)
```

## 操作

### create — 新規作成

1. 作業をユーザーと合意済みの粒度で項目に分解する。各項目は「1 セッションで完了し、完了を検証できる」単位にする
2. 上記フォーマットでファイルを作成し、パスをユーザーに伝える

### resume — 再開（セッション開始時・タスク切替時）

1. `ls ~/.agents/workplans/<リポジトリ名>/` で該当 workplan を探して読む
2. `in-progress` に項目があればそこから再開する。空なら `next` の先頭を `in-progress` に移して着手する
3. `blocked` の項目は待ち条件が解消していないか確認する（例: PR がマージされたか）。解消していれば `next` に戻す

### status — 状況報告

workplan の現状（done 件数 / in-progress / next 残数 / blocked 理由）を要約して報告する。

## 運用ルール

- **1 項目完了ごとに更新する**: 完了項目を `done` に移し（日付・PR 番号付き）、`next` の先頭を `in-progress` に移して**確認を求めずに続行する**。ユーザーへの「次に進めていいですか？」は禁止 — next に積んだ時点で承認済みとみなす
- **止まってよいのは 3 条件のみ**: ① `next` が空 ② 残りが `blocked` だけ ③ 判断がユーザーにしかできない論点が出た（その場合は論点を `blocked` に記録してから聞く）
- **人待ちは Monitor に委ねる**: マージ待ち・CI 待ち・レビュー待ちは `blocked` に理由を書き、可能なら Monitor を登録して通知駆動で再開する
- **ユーザーの新しい指示は workplan より常に優先する**: 矛盾したら workplan 側を更新する
- **計画変更は履歴を残す**: 項目の削除ではなく取り消し線 + 理由（例: `~~xxx~~ #123 で不要になった`）で残す
