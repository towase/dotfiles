# dotfiles

## 管理方針

- `brew`: OS 管理（OS基盤・アプリ基盤・aqua非対応ツールの例外）
- `aqua`: CLI 管理（原則すべてのCLI）
- `mise`: runtime 管理（言語・実行環境のバージョン）
- `chezmoi`: dotfile 管理（ホーム配下の symlink / 設定ファイル）

## 責務マトリクス

| 対象                  | 管理先   | 定義ファイル                      | 備考                       |
| --------------------- | -------- | --------------------------------- | -------------------------- |
| OS基盤ツール          | Homebrew | `Brewfile`                        | macOSセットアップ向け      |
| CLIツール（原則）     | aqua     | `aqua.yaml`                       | `gh`, `jq`, `ripgrep` など |
| runtime               | mise     | `mise.toml`                       | 例: `node`, `terraform`    |
| 例外CLI（aqua非対応） | Homebrew | `Brewfile`                        | 理由コメントを必須で付与   |
| ホーム配下の dotfile  | chezmoi  | `dot_*` / `symlink_*.tmpl` 各ファイル | ホームへ symlink を配置 |

## 初期セットアップ

1. [Homebrew の `.pkg` インストーラ](https://github.com/Homebrew/brew/releases/latest) をダウンロードして実行する。
2. このリポジトリを `~/src/github.com/towase/dotfiles` にクローンする（ghq 運用前提）。
3. `./setup.sh` を実行する。
4. `./install.sh` を実行する。

`setup.sh` の役割:
- macOS設定の適用

`install.sh` の役割:
- `brew`（OS基盤）導入・反映
- `aqua`（CLI）導入・反映
- `mise`（runtime）導入・反映
- `chezmoi` の sourceDir 設定と `chezmoi apply` によるホーム配下の symlink 展開

期待結果:
- CLIは `aqua.yaml` 由来で利用可能になる。
- runtimeは `mise.toml` 由来で利用可能になる。
- OS基盤と例外ツールは `Brewfile` 由来で利用可能になる。
- ホーム配下の dotfile は `chezmoi apply` 由来で配置される。

## 日常運用

追加・更新・削除時は、変更対象を先に決めてから編集します。

- CLIを追加/更新/削除する: `aqua.yaml` を編集する。
- runtimeを追加/更新/削除する: `mise.toml` を編集する。
- OS基盤または例外CLIを追加/更新/削除する: `Brewfile` を編集する。
- dotfile を追加/更新/削除する:
  - symlink 経由で管理されるファイル（`.zshrc` / `.gitconfig` / `.claude/settings.json` / `AGENTS.md` 経由の `CLAUDE.md` 等）はリポジトリ内の実体ファイルを直接編集するだけで反映される。
  - chezmoi が実体コピーとして管理するファイル（`dot_agents/skills/<name>/SKILL.md` など）はリポジトリ内のソースを編集したあと `chezmoi apply` で反映する。
  - 新規に dotfile を管理対象に加える場合は、`dot_<name>` ディレクトリ / `symlink_dot_<name>.tmpl` を作成し、必要に応じて `.chezmoiignore` を更新する。

## chezmoi 運用メモ

- `sourceDir` はこのリポジトリ自体（`~/src/github.com/towase/dotfiles`）。`install.sh` が `~/.config/chezmoi/chezmoi.toml` を生成する。
- ホーム配下への配置は原則 symlink（`symlink_*.tmpl`）でこのリポジトリを指す。実体編集がそのまま反映される。
- リポジトリ直下の非 dotfile（`README.md` / `Brewfile` など）は `.chezmoiignore` で配置対象から除外している。
- 現在の差分を確認するには `chezmoi diff`、反映は `chezmoi apply`。

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
- dotfile 管理は `setup.sh` の `ln -sf` 列挙から `chezmoi` に移行済み（issue #1）。
