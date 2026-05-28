---
name: frontend-verify
description: |
  フロントエンドを実装した直後に Claude 自身が chrome-devtools MCP で実画面を開き、
  機能性 / UX デザイン 4 原則（近接・整列・反復・強弱対比）/ よくある UI 不具合
  （プルダウン折り返し・モーダル位置・レスポンシブ崩れ・フォーカス可視性など）を
  観点別に判定し、スクリーンショット付き HTML レポートを出力する skill。
  「フロントエンド実装後の確認」「UI チェック」「動作確認して」「実装後のチェック」
  「ブラウザで確認して」と言及された際、または HTML / CSS / *.jsx / *.tsx / *.vue /
  *.svelte / *.astro の編集直後のセルフチェックとして使用する。
argument-hint: "[url-or-path] [viewport:mobile,tablet,desktop] [skip:functional|ux|common]"
---

# Frontend Verify — 実装直後の動作 + UX セルフチェック

フロントエンドを実装した直後（PR 作成前 / コミット前）に、Claude 自身が `chrome-devtools` MCP で実画面を開き、
**機能性 + UX デザイン原則 + よくある UI 不具合** の 3 観点でセルフチェックし、結果をスクリーンショット付き HTML レポートにまとめる。

`verify` / `run` は動作確認まで、`review-multi-agent` はコード視点のレビュー。本 skill は **実画面を動かして UX 観点まで踏み込んで判定する** 領域を担う。
コード修正は行わない。

## いつ使うか

- フロントエンドコード（HTML / CSS / *.jsx / *.tsx / *.vue / *.svelte / *.astro 等）を編集した直後
- ユーザーが「動作確認して」「UI チェックして」「フロントエンド実装後の確認」「ブラウザで確認して」と明示した時
- PR 作成前のセルフチェックとして

## 観点ファイル

3 つの観点ファイルを `checklists/<name>.md` に分割。各観点に入る直前に対応ファイルを Read するため、最初は本 SKILL.md だけ読めば十分（token 効率）。

| ファイル | 観点 |
|----------|------|
| `checklists/functional.md` | 主要フロー実行 / 状態網羅 / コンソールエラー / バリデーション / 二重送信防止 |
| `checklists/ux-principles.md` | 近接 / 整列 / 反復 / 強弱対比（ロビン・ウィリアムズの 4 原則） |
| `checklists/common-issues.md` | プルダウン折り返し・モーダル位置・フォーカス可視性などの「ありがちな崩れ」 |

## 引数

- `<url-or-path>` — チェック対象 URL（`http://localhost:3000/...`）。省略時は Phase 0-2 で対話的に決定
- `viewport:<list>` — `mobile`(375px) / `tablet`(768px) / `desktop`(1280px)、カンマ区切り。省略時は 3 つ全て
- `skip:<list>` — `functional` / `ux` / `common` をカンマ区切り。省略時はスキップなし

## Phase 遷移

```text
Phase 0 → Phase 1
Phase 1 → Phase 2（サーバ起動成功 / URL 到達可）
Phase 1 → Phase 5（起動失敗 → フォールバック）
Phase 2 → Phase 3（MCP セッション確立）
Phase 2 → Phase 5（chrome-devtools MCP 利用不可 → フォールバック）
Phase 3 → Phase 4（全観点チェック完了）
Phase 4 → 完了（レポート出力 + open）
Phase 5 → 完了（人間向けチェックリスト提示）
```

---

## Phase 0: 対象画面・観点の決定

### 0-1. 引数解析

`$ARGUMENTS` から URL / viewport / skip を抽出。

### 0-2. 対象画面の特定

引数で URL が指定されていればそれを採用。指定がない場合:

1. 現在の差分（`git diff --name-only HEAD` または `git status -uno`）を読み、編集された route / component を特定
2. ルーティング設定（`app/routes/*` / `pages/*` / `src/router/*` / Next.js App Router の `app/**/page.tsx` 等）と突合して候補 URL を導く
3. 候補が複数 or 不明な場合は `AskUserQuestion` で確認

### 0-3. 観点のスキップ判定

`skip:` で指定された観点はチェック対象から外す。

### 遷移
→ **Phase 1**

---

## Phase 1: 開発サーバ起動

### 1-1. 既存サーバの探知

`lsof -i :3000 -i :5173 -i :4173 -i :8080 -i :8000` などプロジェクトの典型ポートを確認し、既にサーバが立っているなら起動をスキップ。
HTTP HEAD で 200 系が返るかも併せて確認。

### 1-2. 起動コマンドの実行

`package.json` の `scripts.dev` / `vite` / `next dev` などプロジェクト固有の起動コマンドを Bash の `run_in_background: true` で実行。
起動完了は HTTP 200 が返るまで Monitor / curl ループで待つ（最大 30 秒）。

### 1-3. 起動失敗時

ログを確認してユーザーに報告し、Phase 5 へフォールバック。

### 遷移
- 起動成功 → **Phase 2**
- 起動失敗 → **Phase 5**

---

## Phase 2: chrome-devtools MCP セットアップ

### 2-1. MCP 利用可能性チェック

`mcp__chrome-devtools__*` ツールが利用可能か確認。利用不可なら Phase 5 へ。

### 2-2. ページを開く

```
mcp__chrome-devtools__list_pages  # 既存タブを再利用できるか確認
mcp__chrome-devtools__new_page    # 新規 or
mcp__chrome-devtools__navigate_page  # 既存タブで URL 変更
```

### 2-3. ビューポート別の初期スクリーンショット

各 viewport で 1 枚ずつフルページスクショ:

1. `mcp__chrome-devtools__resize_page` で width を mobile=375 / tablet=768 / desktop=1280、height=900 程度に設定
2. `mcp__chrome-devtools__navigate_page`（または reload）でレイアウト再計算を確実にする
3. `mcp__chrome-devtools__take_screenshot` でフルページ撮影

スクショは `/tmp/frontend-verify-screenshots-{timestamp}/` に保存し、ファイル名は `initial-{viewport}.png` などで一意化。

### 2-4. コンソール・ネットワーク情報の初期取得

```
mcp__chrome-devtools__list_console_messages
mcp__chrome-devtools__list_network_requests
```

初期ロード時のエラー / 4xx / 5xx を収集して後段の finding 化に備える。

### 遷移
- MCP 利用可 → **Phase 3**
- MCP 利用不可 → **Phase 5**

---

## Phase 3: 観点別チェック実行

`skip:` で外されていない観点を順に実行する。各観点に入る直前に対応する `checklists/<name>.md` を Read して観点リストを取得する。

### 3-1. functional チェック

`checklists/functional.md` を Read。

主要フローを MCP で実行する。代表例:

- フォーム入力: `mcp__chrome-devtools__fill_form` → `mcp__chrome-devtools__click`（送信）→ `mcp__chrome-devtools__wait_for`（成功 or エラー）
- バリデーション: 必須未入力で送信 → エラー表示を `take_screenshot` + `take_snapshot` で確認
- プルダウン: `mcp__chrome-devtools__click`（select）→ 選択肢展開状態を撮影 → `mcp__chrome-devtools__select_page` で値選択
- モーダル: 開く → 撮影 → 背景クリック / Escape で閉じる動作確認
- ナビゲーション: 主要なリンクを 1〜2 本踏む

各操作の前後で `list_console_messages` / `list_network_requests` を取り直し、新規エラー / 失敗リクエストを finding 化。

### 3-2. ux-principles チェック

`checklists/ux-principles.md` を Read。

Phase 2-3 で取得した各 viewport のフルページスクショと、必要なら `mcp__chrome-devtools__take_snapshot` の DOM スナップショットを根拠に、近接 / 整列 / 反復 / 強弱対比の 4 原則を順に判定。
判定には**実画像**を見ること。DOM だけで「コントラスト OK」のような推測はしない。

### 3-3. common-issues チェック

`checklists/common-issues.md` を Read。

代表的な確認手順:

- プルダウン折り返し: 該当 select を `click` で展開 → スクショ → 選択肢が長文だと折り返し / ellipsis / はみ出しのどれか判定
- レスポンシブ崩れ: mobile スクショで横スクロール発生有無を確認
- フォーカス可視性: `mcp__chrome-devtools__press_key` で Tab を 5〜10 回押し、各ステップで `take_screenshot` してフォーカスリングを確認
- モーダル位置: 開いた状態を mobile / desktop それぞれで撮影し、画面端見切れを確認
- クリック領域: `take_snapshot` の bounding box から 24×24 CSS px 未満の主要ボタンを抽出

### 3-4. findings の構造

各 finding は以下を持つ:

| キー | 値 |
|------|----|
| `id` | `F-001`, `F-002`, ... |
| `category` | `functional` / `ux-principles` / `common-issues` |
| `severity` | `blocker` / `major` / `minor` / `nit` |
| `location` | 対象 URL + viewport + 要素テキスト or DOM パス |
| `finding` | 何が問題か（1〜3 文） |
| `suggestion` | 次のアクション |
| `screenshot` | スクショファイルパス（あれば） |

`severity` の目安は各観点ファイル末尾の「severity の目安」表に従う。

### 遷移
→ 全観点完了後 **Phase 4**

---

## Phase 4: レポート出力

### 4-1. レポートパス

- HTML: `/tmp/frontend-verify-{YYYYMMDD-HHMMSS}.html`
- タイムスタンプは `date +%Y%m%d-%H%M%S`、再実行時も上書きしない

### 4-2. HTML レポートの構成

ライトモード固定。`prefers-color-scheme: dark` 分岐や `color-scheme: dark` は入れない。外部 CDN / Web フォント / JS への依存なし、`<style>` inline。

セクション:

1. **メタ情報表**: 対象 URL、viewport 一覧、実行日時、Finding 総数
2. **TL;DR**: severity 別件数 + 重点対応候補（`blocker` > 0 なら blocker のみ、`blocker` = 0 なら major にフォールバック、どちらも 0 なら「該当なし」）
3. **スクリーンショット一覧**: 各 viewport × 主要状態（initial / フォーム入力中 / プルダウン展開 / モーダル / フォーカス）をサムネイル + クリックで拡大
4. **観点別 Findings**: `functional` → `ux-principles` → `common-issues` の順、各カテゴリ内は severity 降順
   - 各 finding カードに `id` / severity バッジ / location / 指摘 / 修正案 / 該当スクショ
5. **コンソール / ネットワークの異常ログ**（あれば）

severity バッジ色: blocker=`#cf222e` / major=`#bc4c00` / minor=`#9a6700` / nit=`#656d76`。
スクショは HTML から相対パスで参照する（同一ディレクトリに置く or `/tmp/frontend-verify-screenshots-{timestamp}/` を相対参照）。

### 4-3. レポートを開く

書き出し後、`open <path>` を実行してブラウザで自動表示。コンソールにはパスと件数サマリだけを 5 行以内で出す。

### 遷移
→ **完了**

---

## Phase 5: フォールバック（MCP 不在 / サーバ起動失敗）

`chrome-devtools` MCP が利用できない、または開発サーバが起動できない場合、Claude は **観点リストを抜粋して人間に確認を依頼する** モードに切り替える。

### 5-1. 観点リストの提示

各 `checklists/<name>.md` から主要観点だけを抜粋し、`/tmp/frontend-verify-checklist-{timestamp}.html` にチェックリスト形式（チェックボックス UI）で書き出して `open`。

### 5-2. 結果の受け取り

ユーザーが各観点に「OK / NG / 気になる」を返した後、Claude は受け取った結果を最終レポート HTML に反映する。MCP が無いので動作根拠（スクショ）は人間の口頭報告のみ。

---

## エッジケース

| ケース | 対処 |
|--------|------|
| 開発サーバが既に立っている | 起動スキップ、既存ポートに接続 |
| 認証が必要な画面 | ユーザーに認証情報入力を依頼するか、認証済みセッションがある前提で進む |
| 複数ページ / 複数コンポーネントを編集 | Phase 0-2 で代表 URL を 1〜3 個に絞る。多すぎる場合は `AskUserQuestion` で選ばせる |
| スクショ撮影に失敗 | エラー内容を finding に含め、スクショ不在を明記 |
| chrome-devtools MCP が応答しない / タイムアウト | Phase 5 へフォールバック |
| 差分が CSS のみ（HTML 構造に変更なし） | 該当画面のスクショ + `ux-principles` + `common-issues` のみ実行（`functional` は skip 推奨） |
| Storybook / 部分コンポーネントのみ存在し、ホスト画面 URL が無い | Storybook URL を対象に取る（`http://localhost:6006/?path=/story/...`） |
| `/tmp` への書き込みに失敗 | カレントディレクトリ直下に `frontend-verify-{...}.html` をフォールバック出力 |

---

## 責務範囲

本 skill は **レポート出力まで**。コード修正は行わない。修正対応は `review-resolve-loop` などの別 skill か、本 skill のレポートをもとにユーザー指示で実施する。
