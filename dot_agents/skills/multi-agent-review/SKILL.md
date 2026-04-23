---
name: multi-agent-review
description: |
  観点（カテゴリ）ごとに sub-agent を並列起動して変更差分をレビューするオーケストレーションスキル。
  カテゴリは「レイヤ系（backend / infrastructure / frontend）」と「品質特性系（security / functionality /
  reliability / usability / maintainability / performance）」の 2 軸をフラットに扱い、ユーザーが選んだ
  カテゴリごとに 1 sub-agent を割り当てる。各カテゴリの観点詳細は `categories/<name>.md` に切り出されており、
  そのファイルをそのまま sub-agent に渡す。
  「multi-agent-review」「観点別レビュー」「カテゴリ別レビュー」「並列レビュー」と言及された際に使用。
argument-hint: "[<pr-number-or-url> | branch:<name> | diff:<base>..<head>] [category,category,...]"
user-invocable: true
---

# Multi-Agent Review — 観点別並列レビューのオーケストレータ

変更差分を、選択されたカテゴリごとに独立した sub-agent でレビューさせ、結果を集約する。
カテゴリ観点の詳細ルール（チェックリスト等）は `categories/<name>.md` に記述されており、
このスキルはそれらを**そのまま**各 sub-agent に渡す責務を持つ。スキル本体は観点の内容を判定しない。

**重要**:
- 各カテゴリ観点ファイルの内容が未記入（プレースホルダ）でも処理は止めず、その旨を最終レポートに明記する。
- sub-agent 並列起動は 1 メッセージ内で複数 `Agent` tool call として送る（逐次ではなく並列実行）。

---

## カテゴリ一覧

### レイヤ系（scope）
どの領域のコードを主対象としてレビューするかを絞り込む。

| slug | 対象 |
|------|------|
| `backend` | サーバサイドのアプリケーションコード |
| `infrastructure` | IaC / CI-CD / コンテナ / ランタイム構成 |
| `frontend` | ブラウザ / モバイル / デスクトップ UI コード |

### 品質特性系（quality-attribute） — 優先順位順
横断的な観点。優先順位はレポート内の並び順・衝突時の重み付けに使用する。

| 優先 | slug | 主眼 |
|------|------|------|
| 1 | `security` | 機密性・認可・入力検証・サプライチェーン |
| 2 | `functionality` | 要求仕様の充足・エッジケース挙動 |
| 3 | `reliability` | 失敗時挙動・冪等性・整合性・可観測性 |
| 4 | `usability` | 使用者（人・API 呼び出し元）の体験 |
| 5 | `maintainability` | 可読性・凝集度・テスト容易性・依存関係 |
| 6 | `performance` | 計算量・リソース効率・スループット |

---

## Phase 遷移

```text
Phase 0 → Phase 1（常に）
Phase 1 → Phase 2（差分が空でない）
Phase 1 → Phase 5（差分が空）
Phase 2 → Phase 3（カテゴリが 1 件以上選択された）
Phase 2 → Phase 5（カテゴリ 0 件 = ユーザーキャンセル相当）
Phase 3 → Phase 4（全 sub-agent 完了）
Phase 4 → Phase 5（常に）
```

---

## Phase 0: 引数解析とスコープ決定

### 0-1. 引数解析

`$ARGUMENTS` から以下を抽出:

- **レビュー対象** (いずれか 1 つ):
  - PR 番号 or URL (`#123`, `https://github.com/...`)
  - `branch:<name>` — 指定ブランチと既定 base の差分
  - `diff:<base>..<head>` — 任意 revision 範囲
  - 省略時: 現在ブランチと `main`（or `master`）の差分
- **カテゴリ**: カンマ区切り slug（例: `backend,security,reliability`）
  - 省略時: Phase 2 でユーザーに選択させる
  - `all` 指定時: 全カテゴリ

### 0-2. 作業ブランチの取り扱い

レビュー対象はワークツリーを変更しない。現在のブランチ・作業状態は維持する。

### 遷移
→ **Phase 1**（例外なし）

---

## Phase 1: 差分収集

### 1-1. 差分の特定

対象種別に応じて以下のいずれかを使用:

```bash
# PR 指定
gh pr diff {PR番号} --repo {owner}/{repo}

# branch 指定
git diff {base}...{branch}

# diff 指定
git diff {base}..{head}

# 省略時（現在ブランチ vs main）
git diff main...HEAD
```

### 1-2. 変更ファイル一覧

```bash
git diff --name-status {base}...{head}
```

### 1-3. 差分が空の場合

Phase 5（完了報告）へ直行し「レビュー対象の差分がない」旨を表示する。

### 遷移
- 差分あり → **Phase 2**
- 差分なし → **Phase 5**

---

## Phase 2: カテゴリ選択

### 2-1. 引数でカテゴリ指定済みの場合

指定された slug を検証し、`categories/` に対応ファイルがあるもののみ採用する。
未知の slug があればユーザーに警告し、残りのカテゴリで続行するか確認する。

### 2-2. カテゴリ未指定の場合

`AskUserQuestion` で以下を提示して複数選択させる:

```markdown
## レビューカテゴリの選択

以下のカテゴリから、今回実行したいものを選んでください（複数選択可）。

### レイヤ系
- [ ] backend
- [ ] infrastructure
- [ ] frontend

### 品質特性系（優先順位順）
- [ ] security
- [ ] functionality
- [ ] reliability
- [ ] usability
- [ ] maintainability
- [ ] performance
```

変更ファイル一覧（Phase 1-2）から、明らかに関連しないレイヤ系カテゴリはデフォルト外してよいが、
**最終決定はユーザーに委ねる**。スキル側で自動で除外しない。

### 遷移
- 1 件以上選択 → **Phase 3**
- 0 件 → **Phase 5**（キャンセル扱い）

---

## Phase 3: Sub-agent 並列起動

### 3-1. 各 sub-agent へ渡す入力

選択カテゴリ数ぶん、**1 メッセージ内に複数の `Agent` tool call** を並べて並列起動する。
各 tool call の `prompt` には以下を自己完結的に含める:

1. **レビュー対象の差分**（Phase 1 で取得した `git diff` / `gh pr diff` の出力全文、または差分が大きい場合は変更ファイル一覧 + base/head の指定）
2. **カテゴリ観点ファイルの内容**: `categories/{slug}.md` を **Read して本文をそのまま埋め込む**
3. **出力フォーマット指示**（後述 3-3）
4. **プロジェクト規約の参照指示**: リポジトリ直下の `AGENTS.md` / `CLAUDE.md` / `docs/` を必要に応じて参照してよい旨

`subagent_type` は原則 `general-purpose`。将来特化エージェントを用意した場合はカテゴリごとに差し替え可能。

### 3-2. 観点ファイルが未記入の場合

`categories/{slug}.md` の本文が未記入（TODO のみ）であっても sub-agent は起動する。
sub-agent には「観点詳細が未整備のため、一般常識ベースで当該カテゴリの最低限のチェックを行うこと」と指示を追加する。
この状態は最終レポートに明示する（Phase 4-2）。

### 3-3. Sub-agent 出力フォーマット

各 sub-agent には以下の JSON 風 Markdown を返すよう指示する:

```markdown
## Category: {slug}

### Summary
{2-3 文で総評}

### Findings
| severity | location | finding | suggestion |
|----------|----------|---------|------------|
| blocker / major / minor / nit | {path}:{line} | {問題点} | {修正案} |

### Notes
- 観点ファイル未整備フラグ: {true / false}
- その他補足
```

### 遷移
→ 全 sub-agent 完了後 **Phase 4**

---

## Phase 4: 結果集約

### 4-1. 優先順位順に並べる

品質特性系は **優先順位順**（security → functionality → ... → performance）。
レイヤ系はその後ろに並べる。

### 4-2. 集約レポート

```markdown
## Multi-Agent Review 結果

**対象**: {PR / branch / diff の識別子}
**カテゴリ**: {選択されたカテゴリ一覧}
**観点ファイル未整備**: {該当 slug の一覧 / なし}

---

{各カテゴリの sub-agent 出力を優先順位順に連結}

---

### 全体サマリ
- blocker: {件数} / major: {件数} / minor: {件数} / nit: {件数}
- 重点対応候補: {blocker と major を上から 3-5 件ピック}
```

### 4-3. Findings の重複排除（努力目標）

同一 `location` + 類似 `finding` が複数カテゴリから挙がった場合、1 件にまとめて「複数カテゴリから指摘」と注記してよい。ただし判断が難しい場合は**重複を許容して全て残す**。欠落のほうが誤集約より害が大きい。

### 遷移
→ **Phase 5**（例外なし）

---

## Phase 5: 完了報告

Phase 4 のレポートをユーザーに提示して終了する。**コード変更は行わない**（本スキルはレビューのみ）。
修正対応は別スキル（例: `review-resolve-loop`）や手作業で行う。

---

## エッジケース

| ケース | 対処 |
|--------|------|
| 差分が巨大（例: 5000 行超） | sub-agent に `git diff` 全文ではなくファイル一覧 + `base..head` を渡し、agent 側で必要箇所のみ読むよう指示 |
| 観点ファイルが全カテゴリ未記入 | 処理は続行。最終レポート冒頭に警告を大きく表示 |
| 一部 sub-agent が失敗 | 他カテゴリの結果は出す。失敗カテゴリは「実行エラー」として列挙 |
| カテゴリ未知 slug | ユーザーに提示して続行可否を確認 |
| PR が存在しないリポジトリ | `gh pr diff` が失敗 → ユーザーに報告し中断 |
| 対象ブランチが base と同一 | Phase 1 で差分 0 と判定 → Phase 5 へ |

---

## 拡張ポイント（将来）

- カテゴリごとに専用 `subagent_type` を用意（例: `security-reviewer`）し、`categories/<slug>.md` 冒頭の frontmatter で指定できるようにする
- `categories/<slug>.md` に静的解析ツールの実行コマンドを記述し、sub-agent 起動前にそれを走らせて結果を添付する
- レイヤ系スコープに応じて差分をフィルタして sub-agent に渡す（現状はフル差分を渡している）
