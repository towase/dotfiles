---
name: implement-with-notes
description: SPEC を実装しながら、spec に書かれていなかった判断・変更せざるを得なかった点・トレードオフ・その他ユーザーが知っておくべき事項を、running の HTML 実装ノートに記録し続ける skill。ノートは実装の最初に作り始め、判断が発生するたびに追記し、実装完了時にブラウザで開く。「ノートを取りながら実装して」「implementation notes を残して実装」「implement-with-notes」と明示的に指示されたときに使用。
disable-model-invocation: true
---

SPEC を実装し、それと並行して「spec に書かれていなかったこと」を記録する running の実装ノート（HTML）を残す。
ノートの目的は、後でユーザーが「なぜこの実装になったのか」「何を勝手に決めたのか」「何を妥協したのか」を一目で把握できるようにすること。

## 引数

$ARGUMENTS

実装する SPEC。次のいずれか:

- インラインのテキスト（要件をそのまま記述）
- spec ファイルへのパス（例 `docs/spec/login.md`）→ 読み込む
- issue / PR の URL → 内容を取得する

SPEC が空、または曖昧で実装の判断ができない場合は、実装を始める前に質問して明確にする（CLAUDE.md「不明瞭な指示は質問」）。

## ノートファイル

- 置き場所: `/tmp/implementation-notes-<topic>.html`（`<topic>` は SPEC 内容から決める kebab-case）
- **running**: 実装の最初にスケルトンを作り、判断が発生するたびに追記する。最後にまとめて書かない
- ライトモード固定。`prefers-color-scheme: dark` や `color-scheme: dark` を入れない（CLAUDE.md 準拠）
- 同名 topic の既存ファイルがある場合は上書きせず、その続きとして追記する（中断した実装の再開とみなす）
- **`open` は実装完了時に 1 回だけ**実行する。スケルトン作成時点では開かない

### スケルトンのテンプレート

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>実装ノート: <SPEC タイトル></title>
<style>
  :root { color-scheme: light; }
  body { font-family: -apple-system, "Hiragino Kaku Gothic ProN", sans-serif; max-width: 920px; margin: 2rem auto; padding: 0 1rem; background: #fff; color: #1a1a1a; line-height: 1.7; }
  h1 { border-bottom: 2px solid #333; padding-bottom: .4rem; }
  .spec { background: #f5f5f5; border-left: 4px solid #888; padding: .8rem 1rem; border-radius: 4px; }
  .entry { border: 1px solid #e0e0e0; border-radius: 6px; padding: .8rem 1rem; margin: 1rem 0; }
  .badge { display: inline-block; font-size: .75rem; padding: .1rem .5rem; border-radius: 999px; color: #fff; }
  .badge.decision { background: #2563eb; }
  .badge.change   { background: #d97706; }
  .badge.tradeoff { background: #7c3aed; }
  .badge.assume   { background: #059669; }
  .badge.open     { background: #dc2626; }
  .entry h3 { margin: .3rem 0; }
  .meta { color: #666; font-size: .85rem; }
  code { background: #f0f0f0; padding: .1rem .3rem; border-radius: 3px; }
  .summary { background: #fafafa; border: 1px solid #ddd; border-radius: 6px; padding: 1rem; }
</style>
</head>
<body>
<h1>実装ノート: <SPEC タイトル></h1>
<p class="meta">対象: <SPEC の出典/パス/URL> · 開始: <YYYY-MM-DD></p>
<div class="spec"><strong>SPEC 概要:</strong> <1〜3 行の要約></div>

<h2>記録</h2>
<!-- ENTRIES: この行のすぐ上に新しいエントリを追記する -->

<h2>サマリ</h2>
<div class="summary"><!-- 実装完了時に記入 --></div>
</body>
</html>
```

### エントリの追記方法

新しいエントリは `<!-- ENTRIES: ... -->` の行の **直前** に Edit で挿入する。これで時系列順（上が古い）に並び、HTML が常に valid に保たれる。

```html
<div class="entry">
  <span class="badge decision">判断</span>
  <h3>短い要約（このエントリで何を決めた/変えたか）</h3>
  <p>詳細: なぜそうしたか、影響範囲。却下した代替案があれば併記する。</p>
  <p class="meta">関連: <code>path/to/file.ts:42</code></p>
</div>
```

badge の種別と class:

| 種別 | class | 何を書くか |
| --- | --- | --- |
| 判断 | `decision` | spec に無かったが実装上決めたこと |
| 変更 | `change` | spec の記述から変えざるを得なかったこと（理由必須） |
| トレードオフ | `tradeoff` | 採用案と犠牲にしたもの、却下した代替案 |
| 前提 | `assume` | spec に明示がなく置いた仮定（誤っていれば手戻りになる箇所） |
| 未解決 | `open` | この実装で解決しきれず残した点 / 要確認 / TODO |

## 記録する / しない

**記録する**（spec に対する差分・補足）:

- spec に書かれていなかったが実装上決めた判断
- spec の記述どおりに作れず変更した点
- トレードオフ（採用案と却下案、犠牲にしたもの）
- 置いた前提・仮定、未解決事項、既知の制約、外部依存、その他ユーザーが知っておくべきこと

**記録しない**（ノイズになる）:

- spec どおりにそのまま実装できた自明な部分
- git が記録する履歴的情報（「〜を追加した」等の作業ログ）
- ノートのためのノート（実装に影響しない感想）

## プロセス

1. **SPEC を取得・把握する**。パス/URL なら読み込む。曖昧なら質問して明確化する
2. **ノートのスケルトンを作成**する（上のテンプレート）。タイトル・出典・開始日・SPEC 概要を埋める。この時点では `open` しない
3. **実装する**。リポジトリ既存のテスト戦略・開発慣習・CLAUDE.md の開発スタイル（原則 TDD、ただし既存慣習に見合う範囲）に従う
   - 実装中、spec に無い判断・変更・トレードオフ・前提・未解決事項に直面するたびに、**実装を先に進める前に**ノートへ 1 エントリ追記する（後回しにしない＝ running を維持）
4. **サマリを記入**する。実装完了後、`<div class="summary">` に「主要な判断 3〜5 点」「未解決事項」「レビュー時に特に見てほしい箇所」をまとめる
5. **`open <filepath>`** を実行してブラウザ表示する。コンソールには書き出したパスと要点（主要判断・未解決事項）のみ伝える

## やらないこと

- ノートを最後にまとめて書く（running を放棄する）
- 自明な実装までノートに書いてノイズにする
- ダークモード対応を入れる
- SPEC が曖昧なまま当て推量で実装を進める（質問する）
- スケルトン作成や追記のたびに `open` する（open は完了時 1 回）

## 使い分け

- 実装はせず方針だけ詰めたい → `grill-me` / `walk-points`
- 実装後に観点別レビューしたい → `review-multi-agent`
- 実装しながら判断ログを残したい → このスキル
