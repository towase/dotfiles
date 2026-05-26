---
name: review-multi-agent
description: |
  観点（カテゴリ）ごとに sub-agent を並列起動して変更差分をレビューするオーケストレーションスキル。
  カテゴリは「レイヤ系（backend / database / infrastructure / frontend）」と「品質特性系（security /
  functionality / robust-safety / reliability / usability / maintainability / performance）」の 2 軸を
  フラットに扱い、ユーザーが選んだカテゴリごとに 1 sub-agent を割り当てる。各カテゴリの観点詳細は
  `categories/<name>.md` に切り出されており、そのファイルをそのまま sub-agent に渡す。集約結果は
  `/tmp/review-multi-agent-*.{md,html}` に Markdown / HTML 2 形式で書き出し、コンソールには要点のみを提示する。
  対象が PR の場合は findings をユーザーに選ばせて inline コメントとして PR に投稿する。
  「review-multi-agent」「観点別レビュー」「カテゴリ別レビュー」「並列レビュー」と言及された際に使用。
argument-hint: "[<pr-number-or-url> | branch:<name> | diff:<base>..<head>] [category,category,...] [severity:blocker|major|all]"
user-invocable: true
---

# Multi-Agent Review — 観点別並列レビューのオーケストレータ

変更差分を、選択されたカテゴリごとに独立した sub-agent でレビューさせ、結果を集約する。
カテゴリ観点の詳細ルール（チェックリスト等）は `categories/<name>.md` に記述されており、
このスキルはそれらを**そのまま**各 sub-agent に渡す責務を持つ。スキル本体は観点の内容を判定しない。

集約結果は `/tmp/review-multi-agent-*.{md,html}` に **Markdown と HTML の 2 形式**で出力する。
ターミナルでの確認・`grep` 用に Markdown を、ブラウザでの可視化用に HTML を、それぞれ**同じ内容**で書き出す。
コンソールには要点（レポートパス・件数・重点対応候補）だけを出し、長いレビュー本文はファイルに集約することで
画面上の見通しを保つ。**ユーザーへは「詳細はレポートファイルを参照してください（HTML は `open` でブラウザ表示できます）」と明示的に案内する**。

**Severity フィルタ（デフォルト挙動）**: 大量指摘で見通しが悪くなるのを防ぐため、デフォルトでは
**sub-agent に `blocker` / `major` のみ報告させる**（minor / nit は最初から収集しない）。
重点対応候補や PR 投稿候補の選定では、**blocker が 1 件以上あれば blocker のみを推す。blocker が
0 件のときに限って major にフォールバックする**。引数 `severity:<level>` で上書き可能。

**重要**:
- 各カテゴリ観点ファイルの内容が未記入（プレースホルダ）でも処理は止めず、その旨を最終レポートに明記する。
- sub-agent 並列起動は 1 メッセージ内で複数 `Agent` tool call として送る（逐次ではなく並列実行）。
- レポートファイルは `Write` tool で `/tmp/` 配下に新規作成する。**Markdown と HTML を同名（拡張子のみ異なる）で 2 ファイル**書き出す。タイムスタンプを名前に含めるため、再実行時も上書きしない。

---

## カテゴリ一覧

### レイヤ系（scope）
どの領域のコードを主対象としてレビューするかを絞り込む。

| slug | 対象 |
|------|------|
| `backend` | サーバサイドのアプリケーションコード |
| `database` | DB スキーマ・制約・インデックス・マイグレーション・トランザクション |
| `infrastructure` | IaC / CI-CD / コンテナ / ランタイム構成 |
| `frontend` | ブラウザ / モバイル / デスクトップ UI コード |

### 品質特性系（quality-attribute） — 優先順位順
横断的な観点。優先順位はレポート内の並び順・衝突時の重み付けに使用する。

| 優先 | slug | 主眼 |
|------|------|------|
| 1 | `security` | 機密性・認可・入力検証・サプライチェーン |
| 2 | `functionality` | 要求仕様の充足・エッジケース挙動 |
| 3 | `robust-safety` | 型による不正状態の不可表現化・境界での検証・fail-safe デフォルト・並行/リソース安全 |
| 4 | `reliability` | 失敗時挙動・冪等性・整合性・可観測性 |
| 5 | `usability` | 使用者（人・API 呼び出し元）の体験 |
| 6 | `maintainability` | 可読性・凝集度・テスト容易性・依存関係 |
| 7 | `performance` | 計算量・リソース効率・スループット |

---

## Phase 遷移

```text
Phase 0 → Phase 1（常に）
Phase 1 → Phase 2（差分が空でない）
Phase 1 → Phase 7（差分が空）
Phase 2 → Phase 3（カテゴリが 1 件以上選択された）
Phase 2 → Phase 7（カテゴリ 0 件 = ユーザーキャンセル相当）
Phase 3 → Phase 4（全 sub-agent 完了）
Phase 4 → Phase 5（レビュー対象が PR かつ findings が 1 件以上）
Phase 4 → Phase 7（レビュー対象が非 PR、または findings 0 件）
Phase 5 → Phase 6（投稿対象に選ばれた findings が 1 件以上）
Phase 5 → Phase 7（全件却下）
Phase 6 → Phase 7（投稿完了・失敗問わず）
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
- **Severity threshold**: `severity:<level>` の形で指定（任意）。`level` は以下のいずれか:
  - `blocker` — blocker のみ収集（最も絞り込みが強い）
  - `major` — blocker + major を収集（**省略時のデフォルト**。minor / nit は捨てる）
  - `all` — blocker / major / minor / nit すべて収集（旧挙動。詳細レビューしたいときに使う）
  - 不正値が指定された場合はユーザーに警告し、`major` にフォールバックする

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

Phase 7（完了報告）へ直行し「レビュー対象の差分がない」旨を表示する。

### 遷移
- 差分あり → **Phase 2**
- 差分なし → **Phase 7**

---

## Phase 2: カテゴリ選択

### 2-1. 引数でカテゴリ指定済みの場合

指定された slug を検証し、`categories/` に対応ファイルがあるもののみ採用する。
未知の slug があればユーザーに警告し、残りのカテゴリで続行するか確認する。

**`_` プレフィックスのファイル（例: `_reviewer-stance.md`）はカテゴリではなく共通片のため、
slug 指定・`all` 指定のいずれでもカテゴリ一覧から除外する。** 共通片は Phase 3-1 で
全 sub-agent に横断注入される（カテゴリとしては選択させない）。

### 2-2. カテゴリ未指定の場合

`AskUserQuestion` で以下を提示して複数選択させる:

```markdown
## レビューカテゴリの選択

以下のカテゴリから、今回実行したいものを選んでください（複数選択可）。

### レイヤ系
- [ ] backend
- [ ] database
- [ ] infrastructure
- [ ] frontend

### 品質特性系（優先順位順）
- [ ] security
- [ ] functionality
- [ ] robust-safety
- [ ] reliability
- [ ] usability
- [ ] maintainability
- [ ] performance
```

変更ファイル一覧（Phase 1-2）から、明らかに関連しないレイヤ系カテゴリはデフォルト外してよいが、
**最終決定はユーザーに委ねる**。スキル側で自動で除外しない。

### 遷移
- 1 件以上選択 → **Phase 3**
- 0 件 → **Phase 7**（キャンセル扱い）

---

## Phase 3: Sub-agent 並列起動

### 3-1. 各 sub-agent へ渡す入力

選択カテゴリ数ぶん、**1 メッセージ内に複数の `Agent` tool call** を並べて並列起動する。
各 tool call の `prompt` には以下を自己完結的に含める:

1. **レビュー対象の差分**（Phase 1 で取得した `git diff` / `gh pr diff` の出力全文、または差分が大きい場合は変更ファイル一覧 + base/head の指定）
2. **カテゴリ観点ファイルの内容**: `categories/{slug}.md` を **Read して本文をそのまま埋め込む**
3. **共通レビュワースタンス**: `categories/_reviewer-stance.md` を **Read して本文をそのまま埋め込む**。severity 判定・suggestion 作成時の共通指針として参照する旨を明記する。ファイルが存在しない場合はこのステップをスキップする
4. **Severity threshold の指示**: Phase 0-1 で決定した threshold に従い、以下のいずれかを **明示的に** prompt に含める:
   - `blocker` 指定時: 「**`blocker` の findings のみを Findings 表に含めること**。`major` 以下に該当するものは Notes 欄に件数のみ記録するか、完全に省略してよい」
   - `major` 指定時（デフォルト）: 「**`blocker` と `major` の findings のみを Findings 表に含めること**。`minor` / `nit` は今回出力しないでよい。境界線上の指摘を `blocker` / `major` に過剰評価しないこと（共通スタンス A-3 を厳守）」
   - `all` 指定時: 「全 severity（`blocker` / `major` / `minor` / `nit`）の findings を出力する」
5. **出力フォーマット指示**（後述 3-3）
6. **プロジェクト規約の参照指示**: リポジトリ直下の `AGENTS.md` / `CLAUDE.md` / `docs/` を必要に応じて参照してよい旨

`subagent_type` は原則 `general-purpose`。将来特化エージェントを用意した場合はカテゴリごとに差し替え可能。

### 3-2. 観点ファイルが未記入の場合

`categories/{slug}.md` の本文が未記入（TODO のみ）であっても sub-agent は起動する。
sub-agent には「観点詳細が未整備のため、一般常識ベースで当該カテゴリの最低限のチェックを行うこと」と指示を追加する。
この状態は最終レポートに明示する（Phase 4-5 のメタ情報表 + 末尾の「観点ファイル未整備の警告」セクション）。

### 3-3. Sub-agent 出力フォーマット

各 sub-agent には以下の JSON 風 Markdown を返すよう指示する:

```markdown
## Category: {slug}

### Summary
{2-3 文で総評}

### Findings
| severity | location | finding | suggestion |
|----------|----------|---------|------------|
| blocker / major | {path}:{line} | {問題点} | {修正案} |

### Notes
- 観点ファイル未整備フラグ: {true / false}
- 適用 severity threshold: {blocker / major / all のいずれか}
- 閾値未満で除外した件数（参考値、内訳不要）: {N}
- その他補足
```

> **Findings 表の severity 列**: 適用 threshold に応じて含める severity を限定する。
> `blocker` 指定なら `blocker` のみ、`major` 指定（デフォルト）なら `blocker` / `major` のみ、
> `all` 指定なら全 severity を許容する。閾値未満は表に含めない（件数のみ Notes に記録）。

### 遷移
→ 全 sub-agent 完了後 **Phase 4**

---

## Phase 4: 結果集約とレポート出力

集約結果は `/tmp/` に Markdown と HTML の 2 形式で書き出し、**詳細はファイル（特に HTML をブラウザで開く想定）を正としてユーザーに参照させる**。
コンソール出力は要点のみに抑える。これによりレビュー量が増えても画面が流れにくくなる。

### 4-1. 優先順位順に並べる

品質特性系は **優先順位順**（security → functionality → robust-safety → reliability → usability → maintainability → performance）。
レイヤ系はその後ろに並べる。同カテゴリ内は severity 降順（blocker → major → minor → nit）→ location 昇順。

### 4-2. Findings の重複排除（努力目標）

同一 `location` + 類似 `finding` が複数カテゴリから挙がった場合、1 件にまとめて「複数カテゴリから指摘」と注記してよい。ただし判断が難しい場合は**重複を許容して全て残す**。欠落のほうが誤集約より害が大きい。

### 4-3. Finding ID 付与

後続フェーズで参照するため、全 findings に `F-001`, `F-002`, ... の連番 ID を付ける。
番号順は 4-1 の並び順（品質特性系 → レイヤ系、同カテゴリ内は severity 降順 → location 昇順）。

### 4-4. メトリクス計算

レポートおよびコンソール出力で使うメトリクスを集計する:

- severity 別件数（threshold に応じて。デフォルトは blocker / major のみ集計、minor / nit は 0 表示）
- カテゴリ × severity のマトリクス
- **重点対応候補**（フォールバック方式）:
  - `blocker` が 1 件以上ある場合: **blocker のみを最大 5 件まで列挙**（major 以下は重点候補に含めない）
  - `blocker` が 0 件で `major` が 1 件以上ある場合: **major を最大 5 件まで列挙**（フォールバック）
  - どちらも 0 件: 「該当なし」と明示
  - threshold が `all` の場合でも、フォールバックは blocker → major までで止め、minor / nit までは降りない

### 4-5. レポートファイルの出力

ファイルは **Markdown / HTML の 2 種類**を同じディレクトリに同名（拡張子のみ異なる）で書き出す:

- Markdown: `/tmp/review-multi-agent-{YYYYMMDD-HHMMSS}-{identifier}.md`
- HTML: `/tmp/review-multi-agent-{YYYYMMDD-HHMMSS}-{identifier}.html`

ターミナルでの `cat` / `grep` 用に Markdown を、ブラウザでの可視化用に HTML を、それぞれ**完全に同じ内容**で書き出す（finding ID・並び順・本文・修正案は一致）。
タイムスタンプは `date +%Y%m%d-%H%M%S` で生成し、ベース名（拡張子前まで）を**両ファイルで共有**する。再実行時も上書きしない設計とする。

`identifier` は対象種別に応じて以下を採用し、`/`・空白・`..` 等のファイル名に使えない文字は `-` に置換する:

| 対象 | identifier |
|------|------------|
| PR (`#123` / URL) | `pr-{番号}` |
| `branch:<name>` | `branch-{name}` |
| `diff:<base>..<head>` | `diff-{base}-{head}` |
| 省略時 | `branch-{現在ブランチ名}` |

Markdown 本体は `Write` tool で生成する。構成は以下のテンプレートに従う（HTML 側のテンプレートは後述 4-5-b 参照）:

````markdown
# Multi-Agent Review レポート

| 項目 | 内容 |
|------|------|
| 対象 | {PR / branch / diff の識別子}（`{owner}/{repo}#{PR番号}` など分かれば併記） |
| 実行日時 | {ISO 8601} |
| カテゴリ | {選択カテゴリ一覧} |
| Severity threshold | {blocker / major / all}（{blocker の場合「blocker のみ収集」/ major の場合「blocker + major のみ収集」/ all の場合「全 severity 収集」}） |
| 重点候補のフォールバック適用 | {blocker > 0 のときは「未適用（blocker のみ表示）」/ blocker = 0 のときは「適用済み（major にフォールバック）」} |
| 観点ファイル未整備 | {該当 slug の一覧 / なし} |
| Finding 総数 | {N} |

## TL;DR

- **件数**: blocker {N} / major {N}{ threshold が `all` のときのみ続けて: ` / minor {N} / nit {N}` }
- **重点対応候補**（{`blocker` を抽出 / `major` にフォールバック / 該当なし のいずれか}）:
  - `[F-001]` **blocker** / security / `src/auth.ts:42` — 認可チェックが欠落
  - `[F-002]` **major** / functionality / `src/api/users.ts:88` — ...（フォールバック時のみ major を列挙）
  - ...

> 重点対応候補が 0 件の場合は「該当なし（blocker / major のいずれも検出されず）」と明記する。
> blocker が 1 件以上あるときは major を重点候補に **含めない**（フォールバックは blocker = 0 のときだけ）。

## 目次

- [全体サマリ](#全体サマリ)
- [カテゴリ別 Findings](#カテゴリ別-findings)
  - [Security](#security)
  - ...（選択された分だけ列挙）
- [観点ファイル未整備の警告](#観点ファイル未整備の警告)（該当時のみ）

## 全体サマリ

### Severity 別

| Severity | 件数 |
|----------|------|
| blocker | {N} |
| major | {N} |
| minor | {N or "—"} |
| nit | {N or "—"} |
| **合計** | **{N}** |

> threshold が `blocker` / `major`（デフォルト）のときは minor / nit を収集していないため、
> 件数欄は `—`（収集対象外）と表記する。`all` 指定時のみ実数を表示。

### カテゴリ × Severity

| カテゴリ | blocker | major | minor | nit | 合計 |
|----------|---------|-------|-------|-----|------|
| security | {N} | {N} | {N} | {N} | {N} |
| ... | ... | ... | ... | ... | ... |

## カテゴリ別 Findings

### Security

> **サマリ**: {sub-agent から受け取った 2-3 文の総評}

#### F-001 — `blocker`

- **場所**: `src/auth.ts:42`
- **指摘**: 認可チェックが欠落している。/users/:id/admin エンドポイントで、呼び出し元が admin ロールを持つことを検証していない。
- **修正案**:
  ```typescript
  if (!await requireRole(ctx, "admin")) {
    return Response.json({ error: "forbidden" }, { status: 403 });
  }
  ```

#### F-002 — `major`

...（カテゴリ内の finding を 1 件ずつカード形式で列挙。各カードは ID / severity / location / 指摘 / 修正案を含む）

> Finding が 0 件のカテゴリは「指摘なし」と明示する。

### Functionality

...（以下、選択カテゴリを優先順位順に列挙）

## 観点ファイル未整備の警告

以下のカテゴリは `categories/{slug}.md` が未記入のため、一般常識ベースでのレビューにとどまる:

- `{slug}`
````

#### 4-5-a. ファイル出力時の実装上の注意

- **finding カードの並び順**: 4-1 の並び順をそのまま反映（カテゴリ内は severity 降順 → location 昇順）
- **修正案の埋め込み**: sub-agent が `suggestion` として返した内容をそのまま貼る。コードフェンスを含む場合はテンプレ全体を ` ```` `（4 連バッククォート）でラップしてフェンスを破壊しない
- **アンカーリンク**: GitHub Flavored Markdown 互換のスラッグ（小文字化、空白を `-`、特殊文字除去）で生成
- **巨大化抑制**: 1 finding の `指摘` 本文が 30 行を超える場合は冒頭 30 行 + `（後略、N 行）` で打ち切り
- **空セクションの扱い**: 選ばれていないカテゴリのセクションは生成しない。Finding 0 件のカテゴリは見出しは出すが「指摘なし」とだけ書く

#### 4-5-b. HTML 本体

HTML 本体も `Write` tool で生成する。Markdown と**同じ情報を同じ並び順で**載せ、ブラウザで見やすい単一ファイル（外部 CSS / JS / フォント・画像への依存なし）として作る。`open <path>.html` でそのまま開ける状態を維持すること。

**必須要件**:

- `<!DOCTYPE html>` から始まる完全な HTML 文書を 1 ファイルで出力する
- `<html lang="ja">` を指定し、`<head>` に `<meta charset="UTF-8">` と `<title>Multi-Agent Review レポート — {identifier}</title>` を含める
- CSS は `<style>` 内に inline で完結させる（外部 CDN・Web フォント・JS は使わない）
- スタイルはライトモード固定にする。CSS 変数で配色を定義し、`prefers-color-scheme: dark` などのダークモード分岐は入れない
- severity ごとのバッジ色を以下に揃える: blocker = 赤系（`#cf222e`）、major = 橙系（`#bc4c00`）、minor = 黄系（`#9a6700`）、nit = 灰系（`#656d76`）
- 構成セクションは Markdown と一致させる: メタ情報表 → TL;DR → 目次 → 全体サマリ（Severity 別 / カテゴリ × Severity） → カテゴリ別 Findings → 観点ファイル未整備の警告（該当時のみ）
- 目次（`<nav>`）からセクションへのアンカーリンクは、Markdown の見出し ID と一致させる
- 各 finding カードは ID / severity バッジ / location / 指摘本文 / 修正案を含むブロックとして配置する

**テンプレート（finding 1 件分まで含む最小例）**:

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>Multi-Agent Review レポート — {identifier}</title>
<style>
  :root {
    --bg: #ffffff; --fg: #1f2328; --muted: #656d76;
    --border: #d1d9e0; --code-bg: #f6f8fa; --link: #0969da;
    --blocker: #cf222e; --major: #bc4c00; --minor: #9a6700; --nit: #656d76;
  }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: var(--fg); background: var(--bg);
    max-width: 960px; margin: 0 auto; padding: 2rem 1.5rem; line-height: 1.6; }
  h1, h2, h3, h4 { line-height: 1.25; margin-top: 1.8em; margin-bottom: 0.6em; }
  h1 { font-size: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
  h2 { font-size: 1.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
  a { color: var(--link); text-decoration: none; }
  a:hover { text-decoration: underline; }
  table { border-collapse: collapse; width: 100%; margin: 1em 0; }
  th, td { border: 1px solid var(--border); padding: 0.4em 0.8em; text-align: left; vertical-align: top; }
  th { background: var(--code-bg); }
  code { background: var(--code-bg); padding: 0.1em 0.3em; border-radius: 3px;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace; font-size: 0.9em; }
  pre { background: var(--code-bg); padding: 1em; border-radius: 6px; overflow-x: auto; }
  pre code { background: transparent; padding: 0; }
  blockquote { color: var(--muted); border-left: 0.25em solid var(--border); padding: 0 1em; margin: 1em 0; }
  .badge { display: inline-block; padding: 0.1em 0.6em; border-radius: 10px;
    font-size: 0.8em; font-weight: 600; color: #fff; text-transform: uppercase; }
  .badge-blocker { background: var(--blocker); }
  .badge-major { background: var(--major); }
  .badge-minor { background: var(--minor); }
  .badge-nit { background: var(--nit); }
  .finding { border: 1px solid var(--border); border-radius: 6px;
    padding: 1em 1.25em; margin: 1em 0; }
  .finding-header { display: flex; flex-wrap: wrap; align-items: center; gap: 0.5em; margin-bottom: 0.5em; }
  .finding-id { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--muted); font-weight: 600; }
  .finding-location { color: var(--muted); font-size: 0.95em; }
</style>
</head>
<body>

<h1>Multi-Agent Review レポート</h1>

<table>
  <tr><th>対象</th><td>{identifier}</td></tr>
  <tr><th>実行日時</th><td>{ISO 8601}</td></tr>
  <tr><th>カテゴリ</th><td>{選択カテゴリ一覧}</td></tr>
  <tr><th>Severity threshold</th><td>{blocker / major / all}</td></tr>
  <tr><th>Finding 総数</th><td>{N}</td></tr>
</table>

<h2 id="tldr">TL;DR</h2>
<ul>
  <li><strong>件数</strong>: blocker {N} / major {N}</li>
  <li><strong>重点対応候補</strong>:
    <ul>
      <li><a href="#f-001"><span class="finding-id">F-001</span></a>
        <span class="badge badge-blocker">blocker</span> security / <code>src/auth.ts:42</code> — 認可チェックが欠落</li>
    </ul>
  </li>
</ul>

<nav>
  <h2 id="toc">目次</h2>
  <ul>
    <li><a href="#summary">全体サマリ</a></li>
    <li><a href="#findings">カテゴリ別 Findings</a>
      <ul><li><a href="#security">Security</a></li></ul>
    </li>
  </ul>
</nav>

<h2 id="summary">全体サマリ</h2>
<h3>Severity 別</h3>
<table>
  <tr><th>Severity</th><th>件数</th></tr>
  <tr><td>blocker</td><td>{N}</td></tr>
  <tr><td>major</td><td>{N}</td></tr>
</table>

<h2 id="findings">カテゴリ別 Findings</h2>
<h3 id="security">Security</h3>
<blockquote>サマリ: {2-3 文}</blockquote>

<div class="finding" id="f-001">
  <div class="finding-header">
    <span class="finding-id">F-001</span>
    <span class="badge badge-blocker">blocker</span>
    <span class="finding-location"><code>src/auth.ts:42</code></span>
  </div>
  <p><strong>指摘</strong>: 認可チェックが欠落している。</p>
  <p><strong>修正案</strong>:</p>
<pre><code>if (!await requireRole(ctx, "admin")) {
  return Response.json({ error: "forbidden" }, { status: 403 });
}</code></pre>
</div>

</body>
</html>
```

#### 4-5-c. HTML 出力時の実装上の注意

- **エスケープ**: finding 本文・修正案・カテゴリサマリの中身に含まれる `<` / `>` / `&` / `"` / `'` は HTML エンティティに変換してから挿入する。`<pre><code>...</code></pre>` の内側に流し込むコード本体も**例外なくエスケープする**（コード片がそのまま HTML として解釈されると表示崩れや XSS の原因になる）
- **Finding カードの並び順**: 4-1 の並び順を Markdown と完全に揃える（カテゴリ内は severity 降順 → location 昇順）
- **Finding ID とアンカー**: 各カードに `id="f-{NNN}"`（小文字）を付け、TL;DR の重点候補からアンカーリンクできるようにする。セクション見出しのアンカーは Markdown と同じスラッグ規則（小文字化、空白を `-`、特殊文字除去）で揃える
- **巨大化抑制**: Markdown と同じ閾値（30 行）で打ち切り、末尾に `<p>（後略、N 行）</p>` を追記する
- **空セクションの扱い**: Markdown と同じ規則。Finding 0 件のカテゴリは見出しは出すが本文に「指摘なし」とだけ書く
- **両ファイルの整合性**: 同じ実行内では Markdown と HTML の以下を**必ず一致**させる — finding ID 連番・並び順・件数集計・カテゴリ一覧・threshold 表記。Markdown を正とし、HTML はその写像として組み立てる
- **依存ゼロ**: 外部 CDN / Web フォント / JS は読み込まない。オフラインかつ `open` 一発で表示できる状態を維持する

### 4-6. コンソールサマリ

ファイル出力後、コンソールには以下のみ出す:

```markdown
## Multi-Agent Review 完了

**レポート**:
- Markdown: `/tmp/review-multi-agent-{...}.md`
- HTML: `/tmp/review-multi-agent-{...}.html` （`open` でブラウザ表示）

**Severity threshold**: {blocker / major / all}{フォールバック適用時は「（blocker = 0 のため major にフォールバック）」を併記}

**件数**: blocker {N} / major {N}{ threshold が `all` のときのみ続けて: ` / minor {N} / nit {N}` }

**重点対応候補（上位 3 件）**:
- `[F-001]` **blocker** / security / `src/auth.ts:42`
- `[F-002]` **blocker** / robust-safety / `src/lib/parser.ts:120`
- ...

カテゴリ別件数・各 finding の本文・修正案は上記レポートを参照してください（HTML をブラウザで開くと読みやすいです）。
```

> blocker > 0 のときは重点対応候補を **blocker のみ**で埋める。blocker = 0 のときに限り major を上位から拾う。
> どちらも 0 件のときは「重点対応候補: 該当なし」と 1 行で示す。

### 遷移
- レビュー対象が PR かつ findings が 1 件以上 → **Phase 5**
- それ以外（branch / diff 指定、または findings 0 件） → **Phase 7**

---

## Phase 5: PR コメント投稿の判断

レビュー対象が PR で、かつ 1 件以上の findings がある場合のみ実行する。
ユーザーに、どの findings を PR の inline コメントとして投稿するかを選ばせる。

### 5-1. 投稿候補リストの提示

優先順位順ソート後の findings を、番号付きで一覧表示する。
**投稿候補リストは重点対応候補の決定ロジック（4-4）に揃える**:
blocker > 0 なら blocker のみを候補として表示し、major 以下は別グループ「（参考）major 一覧」に畳む。
blocker = 0 のときに限り major を主候補として表示する。

```markdown
## PR コメント投稿候補

対象 PR: {owner}/{repo}#{PR番号}
Severity threshold: {blocker / major / all}{フォールバック適用時は注記}
投稿候補: {主候補の件数} 件（blocker: N / major: N{ threshold が `all` のときのみ続けて: ` / minor: N / nit: N` }）

### 主候補（blocker > 0 のときは blocker のみ / blocker = 0 のときは major）
- [F-001] **blocker** / security / `src/auth.ts:42`
  認可チェックが欠落している
  → 修正案: ハンドラ冒頭で `requireRole("admin")` を呼ぶ
- ...

### 参考（主候補に含まれなかった検出結果）
- blocker > 0 のときの major 一覧、または threshold が `all` のときの minor / nit 一覧をここに畳む
- 件数のみ示し、必要なら「すべて表示」を `AskUserQuestion` の続きで選ばせる
```

### 5-2. 投稿方針の確認

`AskUserQuestion` で以下の選択肢を提示する。
**選択肢の文言は主候補の severity に応じて動的に組み立てる**（blocker のときは「blocker をすべて投稿」、major フォールバック時は「major をすべて投稿」など）:

- 主候補をすべて投稿（ワンクリック想定の既定）
- 主候補 + 参考 も含めて投稿
- 個別に選択する
- すべて却下（投稿しない）

「個別に選択する」が選ばれた場合は、続けて `AskUserQuestion` で各 finding ID を複数選択として提示し、投稿対象を確定させる。

### 5-3. コメント本文の準備

選ばれた findings ごとに、以下のテンプレートで本文を組み立てる:

```markdown
**[{severity} / {category}]** {finding}

**修正案**: {suggestion}

<sub>_Multi-Agent Review より自動投稿 ({finding_id})_</sub>
```

### 遷移
- 投稿対象 1 件以上 → **Phase 6**
- 0 件（すべて却下） → **Phase 7**

---

## Phase 6: PR コメント投稿

選ばれた findings を、1 本の PR Review にまとめて inline コメントとして投稿する。

### 6-1. 投稿対象 commit の特定

```bash
COMMIT_SHA=$(gh pr view {PR番号} --repo {owner}/{repo} --json headRefOid -q .headRefOid)
```

### 6-2. Review 一括投稿

GitHub REST API の `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` を使い、
`event=COMMENT` で pending でない通常コメントレビューを 1 本作成する。

```bash
gh api \
  --method POST \
  /repos/{owner}/{repo}/pulls/{PR番号}/reviews \
  -f commit_id="$COMMIT_SHA" \
  -f event=COMMENT \
  -f body="Multi-Agent Review: {選択カテゴリ} を対象にレビューを実施しました。" \
  --input <(jq -n '{
    comments: [
      {path: "src/auth.ts", line: 42, side: "RIGHT", body: "..."},
      ...
    ]
  }')
```

（実装時は `gh api` の入力形式に合わせて adjust する。`--input` でファイル or heredoc JSON を渡すのが確実）

### 6-3. inline が付けられない finding のフォールバック

以下のいずれかに該当する finding は、inline コメントとして投稿できないので **PR 全体コメント**
（`POST /repos/.../issues/{pr}/comments`）にフォールバックするか、最終レポートで「未投稿」として列挙する:

- `location` の行が当該 PR の diff 範囲外
- ファイルパスが不明 / リネームで commit 上の path と一致しない
- sub-agent が location を `N/A` として返した

### 6-4. 投稿失敗時

- 1 回だけリトライする。2 回目も失敗した finding は Phase 7 の報告に「投稿失敗」として列挙。
- 全件失敗の場合でも本スキルは中断せず、そのまま Phase 7 へ進む。

### 遷移
→ **Phase 7**（成功・失敗問わず）

---

## Phase 7: 完了報告

コンソールには要点のみを出す。findings の本文・修正案などの詳細は Phase 4-5 で出力したレポートファイルに集約済みなので、**最後に必ずレポートのパスを示してユーザーに参照を促す**。

### 7-1. 出力テンプレート

```markdown
## Multi-Agent Review 完了

**レポート**:
- Markdown: `/tmp/review-multi-agent-{...}.md`
- HTML: `/tmp/review-multi-agent-{...}.html` （`open` でブラウザ表示）

**Severity threshold**: {blocker / major / all}{フォールバック適用時は「（blocker = 0 のため major にフォールバック）」を併記}

### Findings
- 件数: blocker {N} / major {N}{ threshold が `all` のときのみ続けて: ` / minor {N} / nit {N}` }
- 重点対応候補（上位 3 件、blocker > 0 なら blocker のみ / blocker = 0 なら major へフォールバック）:
  - `[F-001]` **blocker** / security / `src/auth.ts:42`
  - ...

### PR コメント投稿（PR 対象時のみ）
- 投稿対象に選ばれた: `F-001`, `F-003`（{N} 件）
- 却下: `F-002`, `F-004`, ...（{N} 件）
- 成功: `F-001` → {review URL}
- 失敗: `F-003` → {エラー要約}
- フォールバック（PR 全体コメント化）: `F-005`

### 案内
findings の本文・修正案・カテゴリ別サマリは上記レポートファイルに記載しています（HTML をブラウザで開くと読みやすいです）。
```

> 投稿が 1 件もない（branch/diff 対象 or 全件却下）場合は「PR コメント投稿」セクション全体を省略する。
> 重点対応候補が 0 件の場合は「該当なし（blocker / major のいずれも検出されず）」と明記する。

### 7-2. スキルの責務範囲

**本スキルの責務は「レビュー実行 → レポート出力 → 投稿判断 → PR コメント投稿」まで**。
コード修正自体は行わない。修正対応は `review-resolve-loop` 等の別スキル、または手作業で行う。

---

## エッジケース

| ケース | 対処 |
|--------|------|
| 差分が巨大（例: 5000 行超） | sub-agent に `git diff` 全文ではなくファイル一覧 + `base..head` を渡し、agent 側で必要箇所のみ読むよう指示 |
| 観点ファイルが全カテゴリ未記入 | 処理は続行。メタ情報表の「観点ファイル未整備」欄に該当 slug を全て載せ、末尾の「観点ファイル未整備の警告」セクションでも明示する |
| 一部 sub-agent が失敗 | 他カテゴリの結果は出す。失敗カテゴリは「実行エラー」として列挙 |
| カテゴリ未知 slug | ユーザーに提示して続行可否を確認 |
| `severity:<level>` の `<level>` が `blocker` / `major` / `all` 以外 | 警告した上で `major` にフォールバックして続行。レポートのメタ情報表にも「不正値を `major` で代替」と注記 |
| threshold = `major`（デフォルト）で sub-agent が誤って minor / nit を返した | Phase 4-1 のソート前に **`minor` / `nit` を捨てる**。捨てた件数だけメタ情報表に「sub-agent が threshold を超えて返した件数」として参考表示 |
| threshold = `blocker` で sub-agent が誤って major を返した | 同様に捨てる。捨てた件数のみ表示 |
| PR が存在しないリポジトリ | `gh pr diff` が失敗 → ユーザーに報告し中断 |
| 対象ブランチが base と同一 | Phase 1 で差分 0 と判定 → Phase 7 へ |
| レビュー対象が非 PR（branch / diff 指定） | Phase 4 後に Phase 5/6 をスキップして Phase 7 へ。投稿先 PR がないため |
| findings が 0 件 | Phase 4 後に Phase 5/6 をスキップして Phase 7 へ（「投稿候補なし」の旨を報告） |
| PR head commit が force-push 等で動いた | Phase 6 投稿時に `gh pr view` で再取得した最新 headRefOid を使用。古い SHA は使わない |
| inline 投稿先行が diff 範囲外 | 6-3 のフォールバック（PR 全体コメント or 未投稿として記録） |
| `gh` 未認証 / 権限不足 | Phase 6 の API コールが失敗 → 全件「投稿失敗」として Phase 7 に列挙し、`gh auth status` の確認を促す |
| `/tmp` への書き込みに失敗 | カレントディレクトリ直下に `review-multi-agent-{...}.md` と `review-multi-agent-{...}.html` を出力するフォールバックに切り替え、コンソールに代替パスを両方案内する。Markdown / HTML どちらか片方だけ失敗した場合も両方を同じディレクトリに揃え直す。それも失敗した場合のみコンソールに Markdown レポート全文を出してユーザーに保存を促す（HTML は省略） |

---

## 拡張ポイント（将来）

- カテゴリごとに専用 `subagent_type` を用意（例: `security-reviewer`）し、`categories/<slug>.md` 冒頭の frontmatter で指定できるようにする
- `categories/<slug>.md` に静的解析ツールの実行コマンドを記述し、sub-agent 起動前にそれを走らせて結果を添付する
- レイヤ系スコープに応じて差分をフィルタして sub-agent に渡す（現状はフル差分を渡している）
