---
name: html-report
description: ユーザーへの確認・レポート用のローカル HTML（/tmp/<topic>.html）を、Claude の HTML Artifact と同じ設計規約（:root トークン配色・和文 Google Fonts・カード / チップ / SVG 図解の部品・レスポンシブ）で書き出す。AGENTS.md の「コミュニケーション」ルールで HTML を書き出すとき、または「HTML で」「ブラウザで見たい」「Artifact と同じ見た目で」と言われたときに使う。
---

# html-report

Artifact tool が公開するページと同じ見た目・構造を、ブラウザで直接開くローカル HTML で再現する。
Artifact では publish 時にサービス側が付ける骨格（doctype・meta・リセット CSS）を、ローカルでは自分で書く。
同梱の `template.html` がその骨格と部品の実例になっている。

## 手順

1. 主題・読者・ページの役割（確認 / レポート）を 1 行で決める。内容の必須要素は AGENTS.md「コミュニケーション」に従う
2. `template.html` を Read する。先頭の `/* Layout: ... */` コメントと `:root` のトークン（配色・フォント）を主題に合わせて決める。迷ったら既定値のままでよい
3. 本文を書く。部品は template.html にある class を使う。使わない部品の CSS は残してよい。template の CSS を書き換えたり足したりするときは、下の「崩れを防ぐ書き方」を守る
4. `/tmp/<topic>.html` に書き出し、`node <この skill の配置先>/scripts/layout-check.mjs /tmp/<topic>.html` でレイアウト検査を通す（下の「検証」）。FAIL が 0 になってから `open <path>` で開く（AGENTS.md の手順）
5. 開いた後に本文や CSS を直したら、もう一度 4 を実行する

## 設計規約

Artifact と同じにする点:

- 完全な HTML 文書として書く。`<!DOCTYPE html>` `<html lang="ja">` `<meta charset>` `<meta name="viewport">` `<title>`。title は 2〜4 語の名前にし、説明を「：」や「—」で足さない
- 色はすべて `:root` のトークン経由で使う。地 `--bg`（白より少し沈めた色）・紙 `--paper`・文字 `--ink`・補助 `--muted`・罫線 `--rule`・アクセント `--accent` と、意味色 `--good` `--major` `--warn` `--bad` `--off`（それぞれ `-soft` の対）。コンポーネントの CSS に色の直書きをしない
- フォントは display（見出し）・body（本文）・mono の 3 役をトークンにする。Google Fonts の和文フォントを `<link>` で読み、Hiragino 系のフォールバックを必ず書く（オフラインでも崩れない）
- 本文 15.5px / line-height 1.8、見出しは display 書体 + `text-wrap: balance`、本文の行幅は 46rem まで、数字が並ぶ所は `font-variant-numeric: tabular-nums`
- 1 カラム中央寄せ（max-width 960px）。要素の間隔は margin ではなく grid / flex の `gap`。横並びは 720px 以下で 1 カラムに畳む
- カード = 紙 + 1px 罫線 + 角丸 10px。チップ = 角丸 999px + soft 背景 + 濃色文字。カードの飾りは「目立たせたい 1 つ」に絞り、全部に同じ影や枠を付けない。意味色（good / warn / bad）はアクセントとは別に使う
- 表・図・コードは `overflow-x: auto` の箱に入れ、ページ本体を横スクロールさせない。grid / flex の子で長文・表・コードを持つものには `min-width: 0`
- 図解はインライン SVG。`svg text { fill: currentColor }` を入れ、線・塗りの色は CSS 変数で指定する。viewBox に外側ラベル分の余白を取り、`.fig svg` の `min-width` で潰れを防ぐ。mermaid はローカルでは描画されないので使わない
- `:focus-visible` の輪郭を出し、`prefers-reduced-motion` を尊重する
- 文章は能動態・短文。装飾目的の絵文字・区切り線・全体中央寄せは使わない。番号は順序に意味があるときだけ付ける
- ありがちな生成デザイン（クリーム地 + セリフ + テラコッタ、紫→青グラデ、Inter / Space Grotesk、絵文字見出し、`rounded-lg` 一律）は避ける

Artifact と変える点:

- ライトモード固定（AGENTS.md）。`:root` に `color-scheme: light` を置き、`prefers-color-scheme: dark` や `[data-theme]` の分岐は書かない
- 外部依存は Google Fonts だけ。JS ライブラリ・CDN・外部画像は使わない。画像が必要なら data URI で埋め込む
- Artifact 向けの `env(safe-area-inset-*)` や `<meta name="claude:viewport-fit-sides">` は書かない

## 崩れを防ぐ書き方

過去のレポートで実際に起きた崩れと、その予防。template.html はこのとおりに書いてあるので、CSS を足すときも同じにする。

| 起きたこと | 原因 | 予防 |
|------|------|------|
| 行の中に入れたリストの文字が、幅 30px の列に押し込まれて 1〜2 文字ごとに折り返した | `.rows li` の子孫セレクタが入れ子の `li` にも効き、行の grid（番号列 + 本文列）になった | リスト部品のセレクタは子セレクタにする（`.rows > li` `.timeline > li` `.pc > li`）。行の中のリストは `ul.d` で書く |
| 選択肢を 3 列に並べたら、案 A の Kotlin コードが幅 300px の列に入って右端が切れ、列の高さもばらばらになった | 多段の grid にコードブロックを入れた | `.options` は最大 2 列（`minmax(min(100%, 360px), 1fr)`）。長いコードを持つ案には `.option.wide` を付けて全幅の 1 段目に置き、短い案をその下に並べる。カード（`.cards`）にはコードを入れない |
| スタックトレース・curl・識別子の多い引用が横スクロールになり、画面幅より長い 1 行を読めなかった | `pre` は折り返さない | 1 行が長いだけのコードは `<pre class="wrap">`（`white-space: pre-wrap`。コピーしても改行は入らない）。自分で書くコードは 1 行 80 字程度で改行する |
| `connector.setProperty("maxLocaleCount", ...)` のような長い識別子がカードの外にはみ出した | 文章の箱に `overflow-wrap` が無い | 文章を入れる箱（`.card p` `.option p` `.pc > li` `.rows .d` `.prose` `td` `.kv dd` `.timeline .what`）には `overflow-wrap: anywhere`。識別子・パス・URL は `<code>` で包む |
| SVG の箱の中の英字ラベルが箱からはみ出した | 文字の長さに箱の幅を合わせていない | 箱の幅は文字数から決める（13px の英字は 1 文字 ≈ 7.5px、太字 ≈ 8px、和文 ≈ 13px）。長い注記は箱の下の段に `text-anchor` で寄せて置き、縦線が別の文字を横切らないようにする |

## 候補フォント（Google Fonts、和文）

| 役割 | 候補 |
|------|------|
| display | Zen Kaku Gothic New（既定）、BIZ UDPGothic、Shippori Mincho B1（読み物・手引き向け） |
| body | Noto Sans JP（既定）、IBM Plex Sans JP |
| mono | ui-monospace / Menlo（既定、Web フォント不要）、IBM Plex Mono |

## 部品の対応表

| 内容 | 部品（template.html の class） |
|------|------|
| メタ情報（対象・日時・SHA） | `header.head` の `.eyebrow` `.meta`、または `.kv` |
| 要点・件数 | `.facts`（数字）、`.cards` |
| 選択肢 + Pros / Cons + 推奨案 | `.options` > `.option`（推奨は `.recommended`、長いコードを持つ案は `.wide`）、`.callout` |
| 調査結果・手順 | `.rows`（番号付き。行の中のリストは `ul.d`）、`.flow`、`.timeline` |
| finding / 指摘カード | `.card` + 見出し行 `.card-h`（ID・チップ・location）+ `pre` |
| severity バッジ（4 段階） | `.chip.bad`（blocker）/ `.chip.major`（major）/ `.chip.warn`（minor）/ `.chip.off`（nit） |
| 人が答えるチェックリスト | `input` / `select` / `textarea` の既定スタイルは template に含む。送信先は持たない |
| 引用（コード・ファイルパス・SHA） | `pre` + `.cite`、`code`。1 行が長いログやコマンドは `pre.wrap` |
| 比較 | `.tbl` > `table` |
| 構成図・流れ図 | `figure.fig` > `.canvas` > `svg` + `figcaption` |
| 根拠・読んだもの / 読んでいないもの | `footer.foot` |

## 検証

書き出した HTML に `scripts/layout-check.mjs` をかける。Playwright で Google Chrome を headless 起動し、幅 1280 / 1000 / 640 / 400 で `scripts/layout-check.browser.js` を実行して、崩れの候補を出す。

```bash
node ~/.agents/skills/html-report/scripts/layout-check.mjs /tmp/<topic>.html
```

- 終了コード 0 = FAIL なし。1 = FAIL あり（直してから再実行する）。2 = Playwright が無い（出力の手順どおり、chrome-devtools MCP の `new_page` → `evaluate_script`（`sourcePath` に `layout-check.browser.js`、format は function）で同じ検査をする）
- FAIL の種類: `page-scrolls-sideways`（ページ本体の横スクロール）、`outside-viewport`（画面外に出る要素）、`content-overflows-box`（箱からはみ出す中身）、`text-in-narrow-column`（細い列に押し込まれた文章）、`code-in-narrow-column`（細い列に収まらないコード）、`svg-text-outside-viewbox` / `svg-text-wider-than-box`（SVG の文字のはみ出し）
- warn の `code-scrolls-sideways` は、行を短くするか `pre.wrap` にするかを決める。幅 640 以下で出るものは放置してよい。info の `font-not-loaded` はオフラインなら無視してよい
- Playwright は `~/.npm/_npx/*/node_modules/playwright` か `qb_product_main/frontend/node_modules/playwright` から探す。別の場所にあるなら `PLAYWRIGHT_MODULE_DIR` で指定する
- 検査が動いているかは `node scripts/layout-check.mjs scripts/selftest.html --widths 1000` で確かめる（4 種類の崩れを入れた見本。FAIL が出れば正常）

検査が通ったら `open` で開いて目視する。frontend-verify は使わない（アプリ画面ではない）。
目視の確認点: 図の文字と線が見える、表の列が読める、フォントが読まれている（フォールバックでも崩れない）。
