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

引数で URL が指定されていればそれを採用。指定がない場合は次の手順で **候補 URL 集合** を導出し、最終的に 1〜3 個に絞る。

#### 0-2-a. 差分ファイルの分類

`git diff --name-only HEAD` を実行し、変更ファイルを 3 種類に分ける:

| 種類 | 例 | 確認画面の導き方 |
|------|----|----------------|
| **route 直結ファイル** | `app/users/page.tsx` / `pages/login.tsx` / `src/views/Profile.vue` | フレームワーク規約から URL を直接導出 |
| **共通コンポーネント** | `src/components/Button.tsx` / `lib/ui/Modal.vue` | `grep -rl "Button" src/pages src/app` 等で使用箇所を洗い出し、route 直結ファイルにマップ |
| **グローバル波及** | `src/styles/global.css` / `tailwind.config.ts` / `app/layout.tsx` | プロジェクト全体に影響。代表画面を 1 つ選んで波及検査用に追加 |

#### 0-2-b. 候補 URL 集合の算出

- **直接対象**: route 直結ファイルから導いた URL（必ず含める）
- **共通コンポーネント波及**: grep 結果のうち、直接対象に既に含まれていれば代表確認とみなして追加しない。**直接対象にカバーされない使用画面が 1 つだけ**ある場合は追加候補
- **グローバル波及代表**: グローバル波及ファイルが含まれる場合、直接対象に入っていない代表画面（例: `/dashboard` など、未編集だがレイアウトを使う画面）を **1 つだけ** 波及検査用に追加

#### 0-2-c. 1〜3 個への絞り込み

候補集合のサイズで分岐:

- **0 個**: 差分から URL が導けない → `AskUserQuestion` で URL を直接尋ねる
- **1〜3 個**: そのまま全部採用する（性質が均一 = 全部直接対象 / 全部波及検査 のとき）。性質が混在（直接編集 + 波及検査）するときは `AskUserQuestion` で「直接編集のみ / 波及検査を含む / 1 画面だけ」のように提示してユーザーに選ばせる
- **4 個以上**: `AskUserQuestion` で必ず絞らせる。選択肢は「主要画面 N 個 / 全部 / 個別選択」を用意

#### 0-2-d. CSS や `*.css` のみの差分

差分が CSS のみ（`*.tsx` / `*.vue` 等を含まない）の場合は、Phase 3-1 (`functional`) を skip 推奨（機能ロジックは変わらないため）。`skip:functional` を内部的に有効化して進める。CSS + tsx 混在の場合は skip しない。

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

以下の 2 段階で `mcp__chrome-devtools__*` ツールの利用可否を判定する:

1. **deferred tool スキーマの取得試行**: `ToolSearch` を `query="select:mcp__chrome-devtools__list_pages"` で呼ぶ。スキーマが返らなければ「環境に MCP 自体が無い」と確定 → Phase 5 へ。
2. **最小 MCP 呼び出しの実行**: スキーマが取れたら、実際に `mcp__chrome-devtools__list_pages` を 1 回呼ぶ。`InputValidationError` / `tool not found` / `MCP server not connected` などのエラーで返れば「サーバ未接続」 → Phase 5 へ。両方通ったときに利用可と確定する。

判定の理由（スキーマ取得成功でも MCP server 未起動のケースがあるため、必ず実呼び出しまでクリアする）。

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

### 複数 URL の場合

Phase 0-2 で複数 URL が選ばれた場合、**URL ごとに Phase 2-2〜2-4 と Phase 3-1〜3-3 を繰り返す**。同じ MCP セッション内で `mcp__chrome-devtools__navigate_page` で URL を切り替えるだけでよい（新規タブは作らない）。findings は URL を含む `location` で記録し、Phase 4 で URL ごとに整理する。

並列実行はしない（同じブラウザセッションで複数 URL を同時操作すると状態が混ざる）。直列で URL を切り替える。

### 3-1. functional チェック

`checklists/functional.md` を Read。

主要フローを MCP で実行する。代表例:

- フォーム入力: `mcp__chrome-devtools__fill_form` → `mcp__chrome-devtools__click`（送信）→ `mcp__chrome-devtools__wait_for`（成功 or エラー）
- バリデーション: 必須未入力で送信 → エラー表示を `take_screenshot` + `take_snapshot` で確認
- プルダウン: `mcp__chrome-devtools__click`（select 要素）→ 選択肢展開状態を `take_screenshot` → option を直接 `mcp__chrome-devtools__click` で選ぶ、または `mcp__chrome-devtools__fill_form` で `<select>` の `value` を指定する。`mcp__chrome-devtools__select_page` は **タブ切替用** で HTML `<select>` 操作には使わない
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

セクション（**単一 URL の場合**）:

1. **メタ情報表**: 対象 URL、viewport 一覧、実行日時、Finding 総数
2. **TL;DR**: severity 別件数 + 重点対応候補（`blocker` > 0 なら blocker のみ、`blocker` = 0 なら major にフォールバック、どちらも 0 なら「該当なし」）
3. **スクリーンショット一覧**: 各 viewport × 主要状態（initial / フォーム入力中 / プルダウン展開 / モーダル / フォーカス）をサムネイル + クリックで拡大
4. **観点別 Findings**: `functional` → `ux-principles` → `common-issues` の順、各カテゴリ内は severity 降順
   - 各 finding カードに `id` / severity バッジ / location / 指摘 / 修正案 / 該当スクショ
5. **コンソール / ネットワークの異常ログ**（あれば）

**複数 URL の場合**: 1 ファイルに統合する（URL ごとに別ファイルを作らない）。構成変更点:

- メタ情報表に **対象 URL 一覧** を縦に列挙
- TL;DR の下に **URL ナビ**（アンカーリンクで `#url-1` / `#url-2` ... へジャンプ）を追加
- スクリーンショット一覧と観点別 Findings は **URL ごとにサブセクションに分割**（`### URL: /login` のように見出し）
- Finding ID（F-001, F-002...）は **URL をまたいで通番**、`location` で URL を区別
- TL;DR の重点対応候補にも URL を併記

severity バッジ色: blocker=`#cf222e` / major=`#bc4c00` / minor=`#9a6700` / nit=`#656d76`。
スクショは HTML から相対パスで参照する（同一ディレクトリに置く or `/tmp/frontend-verify-screenshots-{timestamp}/` を相対参照）。

### 4-3. レポートを開く

書き出し後、`open <path>` を実行してブラウザで自動表示。コンソールにはパスと件数サマリだけを 5 行以内で出す。

### 遷移
→ **完了**

---

## Phase 5: フォールバック（MCP 不在 / サーバ起動失敗）

`chrome-devtools` MCP が利用できない、または開発サーバが起動できない場合、Claude は **観点リストを抜粋して人間に確認を依頼する** モードに切り替える。

### 5-0. Phase 5 入り直後のアクション

Phase 5 は Phase 3 を経由しないため、観点ファイルがまだ Read されていない。Phase 5 に入った時点で **`skip:` 指定で外されていない観点ファイル全てを Read する**。

```
Read /Users/towase/.claude/skills/frontend-verify/checklists/functional.md
Read /Users/towase/.claude/skills/frontend-verify/checklists/ux-principles.md
Read /Users/towase/.claude/skills/frontend-verify/checklists/common-issues.md
```

並列 Read してよい。

### 5-1. チェックリスト HTML の生成

`/tmp/frontend-verify-checklist-{YYYYMMDD-HHMMSS}.html` に**人間がブラウザで答える**チェックリストを書き出す。

**「主要観点」の抜粋ルール**: 各観点ファイル末尾の **severity 目安表で `blocker` / `major` に該当する項目を全て採用**。さらに、各観点ファイルの大セクション（A / B / C ...）から **最低 1 項目** は必ず含める（網羅性を担保）。`minor` / `nit` のみのセクションは 1 項目に絞る。

**HTML の中身**（順序）:

1. **メタ情報表**:
   - 対象ファイル一覧（git 差分から）
   - 推奨確認画面 URL
   - 推奨 viewport（mobile / tablet / desktop）
   - **モード理由**: 「chrome-devtools MCP が利用不可」または「開発サーバ起動失敗（理由: {コマンド} / {終了コード} / {ログ末尾}）」を明示
2. **観点別チェックリスト**: functional → ux-principles → common-issues の順。各項目に
   - チェックボックス（「確認した / 未確認」を兼ねる）
   - ラジオ: 「OK / NG / 気になる」
   - 自由記述コメント欄（`<textarea>`）
   - 参照元（観点ファイルの節番号 — 例: `functional.md A-1`）
   - severity 目安バッジ（該当 severity を `4-2` の色規約と同じ色で表示）
3. **ユーザーへの案内文**: 「ブラウザで確認した後、結果をチャットで報告してください」

ライトモード固定、外部依存なし、`<style>` inline、フォーム POST 先は持たない（ユーザーは口頭でチャットに報告）。

書き出し後 `open <path>` で自動表示。

### 5-2. ユーザー結果の受け取り + 最終レポート出力

ユーザーがチェックリストを見て「OK / NG / 気になる + コメント」を返した後、最終レポートを Phase 4 と同じ命名規則で `/tmp/frontend-verify-{YYYYMMDD-HHMMSS}.html` に書き出す（チェックリストの `-checklist-` を除いた名前）。

最終レポートの構成は **Phase 4-2 と同じ**（メタ情報 / TL;DR / 観点別 Findings）。ただし以下の差分:

- **スクリーンショット一覧セクションは省略**（MCP 不在のため取得していない）
- メタ情報表に **モード**: `fallback (MCP 不在)` または `fallback (サーバ起動失敗)` を明記
- Findings は「NG」「気になる」と回答された項目を finding 化。severity は対応する観点ファイルの目安表に従う
- 各 finding カードの末尾に「**根拠**: ユーザー口頭報告」と明記（Phase 4 ではスクショだが、Phase 5 では人間報告が根拠）

書き出し後 `open` で表示し、コンソールには 5 行以内のサマリ（パス / モード / Findings 件数）を出す。

---

## エッジケース

| ケース | 対処 |
|--------|------|
| 開発サーバが既に立っている | 起動スキップ、既存ポートに接続 |
| 認証が必要な画面 | ユーザーに認証情報入力を依頼するか、認証済みセッションがある前提で進む |
| 複数ページ / 複数コンポーネントを編集 | Phase 0-2-c の絞り込みロジックに従う。性質が混在 or 4 個以上なら `AskUserQuestion` で確定させる |
| 共通コンポーネント変更（`src/components/Button.tsx` 等） | Phase 0-2-a で `grep` し、route 直結ファイルにマップ。直接対象に含まれていれば代表確認とみなして追加しない |
| グローバル波及変更（`global.css` / `layout.tsx` / `tailwind.config` 等） | Phase 0-2-b で「波及検査用代表画面」を 1 つだけ追加 |
| スクショ撮影に失敗 | エラー内容を finding に含め、スクショ不在を明記 |
| chrome-devtools MCP が応答しない / タイムアウト | Phase 5 へフォールバック |
| 差分が CSS のみ（HTML 構造に変更なし） | Phase 0-2-d に従う（`functional` を skip）。CSS + tsx 混在の場合は skip しない |
| Storybook / 部分コンポーネントのみ存在し、ホスト画面 URL が無い | Storybook URL を対象に取る（`http://localhost:6006/?path=/story/...`） |
| `/tmp` への書き込みに失敗 | カレントディレクトリ直下に `frontend-verify-{...}.html` をフォールバック出力 |

---

## 責務範囲

本 skill は **レポート出力まで**。コード修正は行わない。修正対応は `review-resolve-loop` などの別 skill か、本 skill のレポートをもとにユーザー指示で実施する。
