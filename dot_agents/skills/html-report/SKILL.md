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
3. 本文を書く。部品は template.html にある class を使う。使わない部品の CSS は残してよい
4. `/tmp/<topic>.html` に書き出し、`open <path>` で開く（AGENTS.md の手順）

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
| 選択肢 + Pros / Cons + 推奨案 | `.options` > `.option`（推奨は `.recommended`）、`.callout` |
| 調査結果・手順 | `.rows`（番号付き）、`.flow`、`.timeline` |
| finding / 指摘カード | `.card` + 見出し行 `.card-h`（ID・チップ・location）+ `pre` |
| severity バッジ（4 段階） | `.chip.bad`（blocker）/ `.chip.major`（major）/ `.chip.warn`（minor）/ `.chip.off`（nit） |
| 人が答えるチェックリスト | `input` / `select` / `textarea` の既定スタイルは template に含む。送信先は持たない |
| 引用（コード・ファイルパス・SHA） | `pre` + `.cite`、`code` |
| 比較 | `.tbl` > `table` |
| 構成図・流れ図 | `figure.fig` > `.canvas` > `svg` + `figcaption` |
| 根拠・読んだもの / 読んでいないもの | `footer.foot` |

## 検証

ブラウザで開いて目視する（`open` 済みのもの）。frontend-verify は使わない（アプリ画面ではない）。
確認点: ページ本体に横スクロールが出ない、フォントが読まれている（フォールバックでも崩れない）、SVG の文字と線が見える。
