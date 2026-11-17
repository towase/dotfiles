# 手動モード（簡易）

Stryker が使えない言語や環境で、AI が本番コードに変異を 1 つずつ入れ、評価するテストを流す。ツールを入れずにどの言語でも使えるが、網羅的ではない。変異を選ぶ AI が、テストを書いた AI と同じ見落としをする恐れもある。そのため、レポートでは「簡易」と明記し、スコアは出さない。

## 使う場面

- `ranges` の `production` に `stryker: false` の言語がある（Kotlin・Go・PHP・Python・シェル・awk など）
- TS/JS だが、Stryker モードの前提（npm、vitest か jest）を満たさない
- `--manual` を指定された

## 変異を選ぶ

選り好みを避けるため、変異は入れる前にすべて書き出す。

1. 範囲の各行に、下の表から当てはまる変異を全部挙げる。AI が面白いと思うものだけを選ばない
   - 構文 1 か所につき、当てはまる表の行ごとに 1 つ挙げる（1 行に置換が 5 本あれば 5 か所として数える）
   - 文字列の定数は仕様に関わるもの（既定値・区切り・出力の形式・外部に渡す名前）だけを対象にする。エラーメッセージの文言は対象にしない
2. 1 回に 40 個まで。超えるときはファイルと範囲から均等に選び、選ばなかった数をレポートに書く。1 回のテストに 30 秒以上かかる（Gradle など）ときは 15 個までにする
3. 挙げた変異を `<workdir>/manual-mutants.json` に書く。結果を見てから変異を足したり消したりしない

| 対象 | 変異 | 例 |
|------|------|------|
| 比較 | `<` と `<=`、`>` と `>=`、`==` と `!=` を入れ替える | `n < max` → `n <= max` |
| 条件 | 条件全体を常に真・常に偽にする | `if ok {` → `if true {` |
| 論理 | `&&` と `\|\|` を入れ替える、否定の `!` を外す | `a && b` → `a \|\| b` |
| 算術 | `+` と `-`、`*` と `/` を入れ替える、`+ 1` を外す | `i + 1` → `i` |
| 定数 | 数値を 0 や ±1 に、文字列を空に、真偽値を反対にする | `limit = 10` → `limit = 11` |
| 戻り値 | 早期 return を消す、戻り値を空・ゼロ値・null にする | `return list` → `return emptyList()` |
| 文の削除 | 副作用のある呼び出し（保存・送信・状態の更新）を消す | `repo.save(x)` を消す |
| 範囲 | slice・substring・ループの境界を ±1 する | `s[1:]` → `s[2:]` |
| エラー | throw を消す、エラーを返さずに成功を返す | Go: `return err` → `return nil` |
| 正規表現 | アンカーの `^` `$` を外す、量指定子を変える | `^\d{4}$` → `\d{4}$` |
| シェル（条件） | `-eq` と `-ne`、`-z` と `-n`、`&&` と `\|\|` を入れ替える、`exit 1` を `exit 0` にする | `[ -z "$x" ]` → `[ -n "$x" ]` |
| シェル（文） | `set -e` や `set -euo pipefail` を消す、コマンド置換の結果を空にする | `v="$(cmd)"` → `v=""` |
| シェル（展開） | `${v//a/b}` と `${v/a/b}`、`${v#p}` と `${v##p}`、`${v%p}` と `${v%%p}` を入れ替える、`${v:-default}` の既定値を消す | `${b//\//__}` → `${b/\//__}` |
| awk | 比較演算を入れ替える、パターンの条件を否定する | `$3 > 0` → `$3 >= 0` |

表に無い構文は近い行に当てはめる。どの行に当てはめたかを、`manual-mutants.json` の `note` に書く。表に無くても、その言語でよく起きる誤りに当たる変異（オプションのフラグを外すなど）は足してよい。足したものも `note` に書く。

```json
{
  "mode": "manual",
  "tests": ["core/src/test/kotlin/com/example/FeeTest.kt"],
  "mutants": [
    {"id": 1, "file": "core/src/main/kotlin/com/example/Fee.kt", "line": 12,
     "operator": "比較", "before": "if (age < 65)", "after": "if (age <= 65)",
     "status": "pending", "note": ""}
  ]
}
```

`status` は `pending`・`killed`・`survived`・`invalid`（コンパイルエラーなどで評価できない）のどれか。

## 1 つずつ入れて流す

変異を入れたコードは想定外の場所に書き込んだり、ファイルを消したりすることがある。テストが HOME や作業ディレクトリに書き込むなら、一時ディレクトリに向けてから流す（`HOME="$(mktemp -d)"` など）。ファイルを消す処理に変異を入れるときは、入れる前に消える場所を確かめる。

変異は Edit で入れても、`manual-mutants.json` を読んで 1 つずつ置き換えるスクリプトで入れてもよい。どちらでも、次の手順を 1 つずつ守る。本番ファイルに未コミットの変更があってもよいように、戻す先は git ではなくバックアップにする。

1. 本番ファイルのバックアップを取る（ファイルごとに最初の 1 回だけ）: `mkdir -p "<workdir>/backup/$(dirname <file>)" && cp -p <file> <workdir>/backup/<file>`
2. 変異を 1 つだけ入れる
3. 構文を確かめる（シェルは `bash -n <file>`、コンパイルする言語はビルド）。ここで落ちたら `invalid` にして、テストは流さずに 5 へ進む
4. 評価するテストだけを流す。差分のテスト以外は流さない。時間制限を付ける（目安はベースラインの 10 倍。`timeout` コマンドが無い macOS では `perl -e 'alarm 60; exec @ARGV' <command>`）

   | 言語 | 例 |
   |------|------|
   | Go | `go test ./pkg/fee/... -run 'TestFee'` |
   | Kotlin / Java（Gradle） | `./gradlew :core:test --tests 'com.example.FeeTest'` |
   | PHP | `vendor/bin/phpunit tests/FeeTest.php` |
   | Python | `pytest tests/test_fee.py` |
   | シェル | `bash scripts/test-fee.sh` |

5. 判定する。テストが落ちたら `killed`、通ったら `survived`、時間切れは `killed`
6. 元に戻す: `cp -p <workdir>/backup/<file> <file>`。続けて `cmp -s <workdir>/backup/<file> <file>` で戻ったことを確かめる。戻っていなければ止める
7. `manual-mutants.json` を更新して、次の変異へ進む

すべて終えたら、本番ファイルがどれもバックアップと同じことを `cmp` でもう一度確かめる。

## 強化と再実行

- 分類・対処・テストの足し方は SKILL.md の手順 4・5 と同じ。`triage.json` の `id` は `manual-mutants.json` の ID を使う
- 変異は書き出し直さない。1 回目の `manual-mutants.json` をそのまま使う
- 再実行の前に、`manual-mutants.json` を `<workdir>/round-<N>.manual-mutants.json` として残す。1 回目に `survived` だった変異の `status` を回ごとに比べ、レポートに 1 回目 → 最後の変化を出す
- 再実行では、対処を「テストを足す」にした変異だけを同じ手順で入れ直す。等価・許容・保留にした変異は入れ直さない。テストを足すだけなら、検出済みの変異が検出されなくなることは無いため。既存のテストを書き換えたときは、全部を入れ直す
- レポートには `killed`・`survived`・`invalid` の数と変異の一覧を出し、スコアは出さない
