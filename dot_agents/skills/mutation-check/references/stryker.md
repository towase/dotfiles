# Stryker モード（TS/JS）

StrykerJS で、差分で変わった行にだけ変異を入れ、評価するテストだけで検出できるかを測る。Stryker は対象のリポジトリに痕跡を残さずに動かす。設定ファイル・結果・一時ディレクトリは `<workdir>` に置き、パッケージは `npm i --no-save` で入れる。

## 前提

- lockfile が `package-lock.json` の npm プロジェクト。pnpm・yarn・bun は依存の記録を変えずに Stryker を入れる方法を確かめていないので対象外。手動モードを使うか、ユーザーに相談する
- テストランナーが vitest か jest。ほかのランナー（mocha、node:test など）は手動モードを使う

## 手順

1. 設定を作る。pkg は `package.json` のあるディレクトリ。

   ```bash
   python3 <skill dir>/scripts/mutation_check.py stryker-config \
     --ranges <workdir>/ranges.json --pkg <pkg> --workdir <workdir>
   ```

   出力の `install` と `run` が次に実行するコマンド。どちらも `cwd`（pkg）で実行する。プロジェクトが mise や nvm で node のバージョンを固定しているなら、そのとおりに前置きを付ける（例: `mise exec -- npx stryker run ...`）。`mutate` と `tests` を見て、範囲が手順 1 で示したものと同じかを確かめる。

2. Stryker を入れる。出力の `install` を、そのまま 1 回で実行する。

   ```bash
   npm i --no-save --no-audit --no-fund @stryker-mutator/core@10.1.1 @stryker-mutator/vitest-runner@10.1.1
   ```

   - `npm i --no-save` をもう一度実行すると、前に `--no-save` で入れたパッケージが消える。足すものがあれば、全部を 1 回のコマンドで入れる
   - 1 回目でも、lockfile に無いパッケージ（手で入れたものなど）が `node_modules` から消えることがある。npm の出力に `removed` があれば、片付けでユーザーに伝える
   - `npm i -D fast-check` のように依存を足したあとは、Stryker も消えているので `install` をやり直す
   - `npx -p @stryker-mutator/core ...` で一時的に入れる方法は使わない。Stryker がプロジェクトの `typescript` を見つけられずに止まる

3. 実行する。出力の `run` を実行する。

   ```bash
   npx stryker run <workdir>/stryker.conf.json
   ```

   目安は、30〜40 個の変異で vitest が約 3 秒、jest（next/jest）が約 10 秒。結果は `<workdir>/mutation.json` と `<workdir>/stryker-report.html`（Stryker の HTML）に出る。

4. 結果をまとめる。次の回で上書きされるので、回ごとに残す。

   ```bash
   cp <workdir>/mutation.json <workdir>/round-1.json
   python3 <skill dir>/scripts/mutation_check.py summarize <workdir>/round-1.json --format md
   ```

   2 回目以降は `--before <workdir>/round-1.json` を付けて、1 回目に生き残った変異がどうなったかを見る。

## 設定の意図

`stryker-config` が書く設定には、次の理由がある。手で直すときも崩さない。

| 設定 | 理由 |
|------|------|
| 設定ファイルを `<workdir>` に置く | 対象のリポジトリに Stryker の痕跡を残さない。`stryker run <設定ファイル>` で外から渡せる |
| `mutate` に `file:開始行-終了行` | 差分で変わった行だけに変異を入れる。終わりの行は行末まで含む。1 つのファイルに複数の範囲を書ける |
| `ignorePatterns` でテストファイルを除き、評価するテストだけを `!` で戻す | 評価するテストだけで検出できるかを測るため。Stryker の `testFiles` は使わない。Stryker 10.1.1 の vitest と jest のどちらでも、`testFiles` を使うとトップレベルの定数のような static な変異が、テストを流しても有効にならず、誤って Survived になった |
| `tsconfigFile` に存在しないパス（TypeScript 7 以上のとき） | Stryker の tsconfig の前処理が TypeScript 7 の API（`ts.parseConfigFileTextToJson`）を呼べずに止まる。ファイルが無ければ前処理を飛ばす |
| `tempDirName` を `<workdir>` の下に、`cleanTempDir: always` | sandbox をリポジトリの外に作り、終わったら消す |
| jest の `projectType: custom` と `configFile` | プロジェクトの jest 設定（next/jest の非同期な設定を含む）をそのまま使う |

## 結果の読み方

| status | 意味 | 扱い |
|------|------|------|
| Killed | テストが落ちた。変異を検出した | 検出 |
| Timeout | 変異で無限ループなどになり、時間切れになった | 検出として数える |
| Survived | 評価したテストが通った | SKILL.md 手順 4 で分類する |
| NoCoverage | 評価したテストのどれも、その箇所を実行しなかった | SKILL.md 手順 4 で分類する（多くは未到達） |
| RuntimeError / CompileError | 変異を評価できなかった | 結果ではない。下の「トラブル対応」 |
| Ignored | 設定で評価の外に出した | `stryker-config` の設定では出ない。出たら設定が書き換わっていないかを見る |

- スコアは `(Killed + Timeout) / (Killed + Timeout + Survived + NoCoverage)`。エラーは数えない
- Stryker 10.1.1 は数値リテラル（`0` や `100`）を変える変異を作らない。スコアが 100% でも、定数や丸め・上下限の値をテストが確かめているかは別に読み、レポートの「確かめてほしいこと」に書く
- `static: true` はモジュールを読み込むときに評価される箇所（トップレベルの定数や正規表現）の変異。Stryker は評価するテストをすべて流して判定する
- Stryker が static な変異について `ignoreStatic` を勧める警告を出しても、`ignoreStatic` は使わない。static な変異を評価の外に出すことになる

## トラブル対応

| 症状 | 原因と対処 |
|------|------|
| `Cannot find package 'typescript'` | `npx -p` で一時的に入れた。手順 2 の `npm i --no-save` で入れ直す |
| `ts.parseConfigFileTextToJson is not a function` | TypeScript 7 以上なのに `tsconfigFile` が設定に無い。`node_modules/typescript` の場所を確かめ、設定に存在しないパスを足す |
| 変異のほとんどが RuntimeError | `summarize` の `errors` の理由を読む。よくあるのは、`.gitignore` された生成コード（OpenAPI のクライアントなど）が無い、評価するテストが import する別のモジュールが読み込みで落ちる。どちらもベースラインの環境を直す |
| `No tests were found` / `No tests were executed` | 評価するテストが、変異を入れるファイルを import していない（vitest は関連するテストだけを流す）。`ignorePatterns` の `!` のパスが pkg からの相対パスになっているかも見る |
| `Initial test run failed` | ベースラインが落ちている。SKILL.md 手順 2 に戻る |
| 遅い | 変異の数を見る。範囲が広すぎるなら pkg や `--tests` で分ける。`stryker-config --concurrency N` で並列数を変えられる |

## 片付け

- `--no-save` で入れたパッケージは `package.json` に載らないので、次の `npm install`・`npm ci`・`npm prune` で消える。スキルは自動では消さない。終わったらユーザーにそう伝える
- `<workdir>/stryker-tmp` は実行のたびに消える。`<workdir>` の結果はレポートの根拠なので残す
