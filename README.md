# dotfiles

macOS の開発環境を再現するための dotfiles リポジトリ。

## 管理対象

| 領域 | 管理先 | 定義ファイル | 方針 |
| --- | --- | --- | --- |
| OS 基盤・アプリ基盤 | Homebrew | `Brewfile` | macOS セットアップ向け。aqua 非対応 CLI の例外もここで管理 |
| CLI ツール | aqua | `aqua.yaml` | 原則すべての CLI を管理 |
| runtime | mise | `mise.toml` | 言語・実行環境のバージョンを管理 |
| ホーム配下の dotfile | chezmoi | `dot_*` / `*.tmpl` / `symlink_*.tmpl` | `chezmoi apply` で配置 |

## 初期セットアップ

1. [Homebrew の `.pkg` インストーラ](https://github.com/Homebrew/brew/releases/latest) をダウンロードして実行する。
2. このリポジトリを `~/src/github.com/towase/dotfiles` にクローンする（ghq 運用前提）。
3. `./setup.sh` を実行する。
4. `./install.sh` を実行する。

| スクリプト | 役割 |
| --- | --- |
| `setup.sh` | macOS 設定を適用する |
| `install.sh` | `brew` / `aqua` / `mise` / npm 配布 CLI 例外を導入し、chezmoi の sourceDir 設定と `chezmoi apply` を実行する |

セットアップ後は次の状態になる。

- CLI は `aqua.yaml` 由来で利用できる。
- runtime は `mise.toml` 由来で利用できる。
- OS 基盤と例外ツールは `Brewfile` 由来で利用できる。
- chezmoi 管理対象のホーム配下 dotfile は `chezmoi apply` 由来で配置される。

## 日常運用

### よく使う編集先

原則として **リポジトリ内のソースを編集してから `chezmoi apply` で反映**する。

| やりたいこと | 編集するソース | 反映 |
| --- | --- | --- |
| `.zshrc` を編集 | `dot_zshrc` | `chezmoi apply` |
| `.gitconfig` を編集 | `dot_gitconfig` | `chezmoi apply` |
| グローバルの `~/.agents/AGENTS.md` / `~/.claude/CLAUDE.md` を編集 | `dot_agents/AGENTS.md` | `chezmoi apply` |
| このリポジトリ用の `AGENTS.md` / `CLAUDE.md` を編集 | `AGENTS.md` / `CLAUDE.md` | 直接編集 |
| skill を編集 | `dot_agents/skills/<name>/` | `chezmoi apply` |
| CLI を追加・更新・削除 | `aqua.yaml` | `./install.sh` または aqua コマンド |
| runtime を追加・更新・削除 | `mise.toml` | `./install.sh` または mise コマンド |
| OS 基盤・例外 CLI を追加・更新・削除 | `Brewfile` | `./install.sh` または brew コマンド |
| npm のみで配布される CLI 例外を追加・更新・削除 | `install.sh` | `./install.sh` |

`dot_agents/AGENTS.md` はグローバル向け agent 指示の単一ソース。`dot_claude/CLAUDE.md.tmpl` が同ファイルを include し、`~/.claude/CLAUDE.md` を生成する。

リポジトリルートの `AGENTS.md` / `CLAUDE.md` は、このリポジトリ専用の project 指示として直接編集する。

### chezmoi 管理対象がホーム配下で直接編集された場合

ツールが chezmoi 管理対象のファイルをホーム配下で直接更新した場合は、source とのドリフトを確認してから取り込む。

1. `chezmoi diff` で差分を確認する。
2. source へ再同期する場合は `chezmoi re-add` を実行する。
3. 手動で調整する場合は `chezmoi merge <target>` を使う。

### 新規ファイルを追加する場合

| 配置方法 | source への追加方法 |
| --- | --- |
| real file として管理 | `dot_<name>` を追加する（例: `dot_tmux.conf`） |
| symlink として配置 | `symlink_dot_<name>.tmpl` に target path を書く |
| chezmoi 管理外にする | リポジトリ直下に置き、`.chezmoiignore` に追記する |

## chezmoi の前提

- `sourceDir` はこのリポジトリ自体（`~/src/github.com/towase/dotfiles`）。`install.sh` が `~/.config/chezmoi/chezmoi.toml` を生成する。
- 原則 real file 管理（`dot_*`）。`symlink_*.tmpl` は topology 上どうしても symlink が必要な場合のみ使う（例: `~/.claude/skills` -> `~/.agents/skills`）。
- リポジトリルートの `AGENTS.md` / `CLAUDE.md` は project 指示として使い、chezmoi の配置対象から除外している。
- `.claude/settings.json` は現在 `.chezmoiignore` で除外しているため、`dot_claude/settings.json` は `chezmoi apply` で反映されない。
- リポジトリ直下の非 dotfile（`README.md` / `Brewfile` など）は `.chezmoiignore` で配置対象から除外している。
- 差分確認は `chezmoi diff`、反映は `chezmoi apply`、逆取り込みは `chezmoi re-add` を使う。

## 例外・更新ルール

- `aqua` 非対応 CLI のみ `brew` に退避する。
- `Brewfile` へ追加する際は、対象行に例外理由コメントを必ず残す。
- `npm` のみで配布される CLI は、repo 管理の Node を使って `install.sh` から `npm install -g` する。
- 自己更新型 CLI は公式インストーラを許容する（例: `curl -fsSL https://claude.ai/install.sh | zsh`）。
- `Brewfile` / `aqua.yaml` / `mise.toml` は月 1 回見直す。
- runtime の更新はローカルで検証してから、必要分のみ `mise.toml` に反映する。
