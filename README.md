# dotfiles

## 管理方針

- `brew`: OS 管理（OS基盤・アプリ基盤・aqua非対応ツールの例外）
- `aqua`: CLI 管理（原則すべてのCLI）
- `mise`: runtime 管理（言語・実行環境のバージョン）

## 責務マトリクス

| 対象                  | 管理先   | 定義ファイル | 備考                       |
| --------------------- | -------- | ------------ | -------------------------- |
| OS基盤ツール          | Homebrew | `Brewfile`   | macOSセットアップ向け      |
| CLIツール（原則）     | aqua     | `aqua.yaml`  | `gh`, `jq`, `ripgrep` など |
| runtime               | mise     | `mise.toml`  | 例: `node`, `terraform`    |
| 例外CLI（aqua非対応） | Homebrew | `Brewfile`   | 理由コメントを必須で付与   |

## 初期セットアップ

1. `./install.sh` を実行する。
2. `./setup.sh` を実行する。

`install.sh` の役割:
- `brew`（OS基盤）導入・反映
- `aqua`（CLI）導入・反映
- `mise`（runtime）導入・反映

`setup.sh` の役割:
- macOS設定の適用
- シェル初期化まわりのセットアップ

期待結果:
- CLIは `aqua.yaml` 由来で利用可能になる。
- runtimeは `mise.toml` 由来で利用可能になる。
- OS基盤と例外ツールは `Brewfile` 由来で利用可能になる。

## 日常運用

追加・更新・削除時は、変更対象を先に決めてから編集します。

- CLIを追加/更新/削除する: `aqua.yaml` を編集する。
- runtimeを追加/更新/削除する: `mise.toml` を編集する。
- OS基盤または例外CLIを追加/更新/削除する: `Brewfile` を編集する。

## 例外ルール

- `aqua` 非対応CLIのみ `brew` に退避する。
- `Brewfile` へ追加する際は、対象行に例外理由コメントを必ず残す。
- 自己更新型CLIは公式インストーラを許容する（例: `curl -fsSL https://claude.ai/install.sh | zsh`）。

## 更新ルール

- `Brewfile` / `aqua.yaml` / `mise.toml` は月1回見直す。
- runtimeの更新はローカルで検証してから、必要分のみ `mise.toml` に反映する。

## 移行メモ

- 旧管理の `volta` / `tfenv` / `gvm` から、runtime管理は `mise` に統一する。
- 新規にruntime管理を追加する場合は、`mise` 以外を増やさない。
