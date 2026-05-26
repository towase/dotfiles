# dotfiles

## 管理方針

- `brew`: OS 管理（OS基盤・アプリ基盤・aqua非対応ツールの例外）
- `aqua`: CLI 管理（原則すべてのCLI）
- `mise`: runtime 管理（言語・実行環境のバージョン）
- `chezmoi`: dotfile 管理（ホーム配下のファイル配置）

## 責務マトリクス

| 対象                  | 管理先   | 定義ファイル                              | 備考                       |
| --------------------- | -------- | ----------------------------------------- | -------------------------- |
| OS基盤ツール          | Homebrew | `Brewfile`                                | macOSセットアップ向け      |
| CLIツール（原則）     | aqua     | `aqua.yaml`                               | `gh`, `jq`, `ripgrep` など |
| runtime               | mise     | `mise.toml`                               | 例: `node`, `terraform`    |
| 例外CLI（aqua非対応） | Homebrew | `Brewfile`                                | 理由コメントを必須で付与   |
| ホーム配下の dotfile  | chezmoi  | `dot_*` / `*.tmpl` / `symlink_*.tmpl`     | `chezmoi apply` で配置     |

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
- `npm` のみで配布されるCLI例外の導入（repo 管理の Node を使用）
- `chezmoi` の sourceDir 設定と `chezmoi apply` によるホーム配下への配置

期待結果:
- CLIは `aqua.yaml` 由来で利用可能になる。
- runtimeは `mise.toml` 由来で利用可能になる。
- OS基盤と例外ツールは `Brewfile` 由来で利用可能になる。
- ホーム配下の dotfile は `chezmoi apply` 由来で配置される。

## 日常運用

### dotfile 編集フロー

原則として **リポジトリ内のソースを編集 → `chezmoi apply` で反映**。

- `.zshrc` を編集: `dot_zshrc` を編集 → `chezmoi apply`
- `.gitconfig` を編集: `dot_gitconfig` を編集 → `chezmoi apply`
- `.claude/settings.json` を編集: `dot_claude/settings.json` を編集 → `chezmoi apply`
- `CLAUDE.md` / `AGENTS.md` を編集: `dot_agents/AGENTS.md` を編集 → `chezmoi apply`（`~/.agents/AGENTS.md` として配置され、`dot_claude/CLAUDE.md.tmpl` が同ファイルを include して `~/.claude/CLAUDE.md` を生成する）
- skill を編集: `dot_agents/skills/<name>/` 配下を編集 → `chezmoi apply`

### ホーム配下で直接編集した場合（逆方向の取り込み）

Claude Code などのツールが `~/.claude/settings.json` を自動更新した場合、そのままだと source にドリフトする。次のいずれかで source へ取り込む:

- `chezmoi re-add` — 現在のホーム配下の状態を source に再同期
- `chezmoi diff` で差分確認後、`chezmoi merge <target>` で手動マージ

### 新規ファイルの追加

- real file として管理: `dot_<name>` を source に追加（例: `dot_tmux.conf`）
- symlink として配置: `symlink_dot_<name>.tmpl` に target path を書く
- chezmoi 管理外のファイル: リポジトリ直下に置き、`.chezmoiignore` に追記

### パッケージ管理

- CLIを追加/更新/削除: `aqua.yaml` を編集
- runtimeを追加/更新/削除: `mise.toml` を編集
- OS基盤または例外CLIを追加/更新/削除: `Brewfile` を編集
- `npm` のみで配布されるCLI例外を追加/更新/削除: `install.sh` を編集

## chezmoi 運用メモ

- `sourceDir` はこのリポジトリ自体（`~/src/github.com/towase/dotfiles`）。`install.sh` が `~/.config/chezmoi/chezmoi.toml` を生成する。
- 原則 real file 管理（`dot_*`）。`symlink_*.tmpl` は topology 上どうしても symlink が必要な場合のみ使う（例: `~/.claude/skills` → `~/.agents/skills`）。
- `CLAUDE.md` / `AGENTS.md` は `dot_agents/AGENTS.md` を単一ソースとし、`dot_claude/CLAUDE.md.tmpl` が chezmoi の include 関数で展開する。リポジトリルートの `AGENTS.md` / `CLAUDE.md` は空のプレースホルダとして残している。
- リポジトリ直下の非 dotfile（`README.md` / `Brewfile` など）は `.chezmoiignore` で配置対象から除外している。
- 現在の差分確認: `chezmoi diff`、反映: `chezmoi apply`、逆取り込み: `chezmoi re-add`。

## 例外ルール

- `aqua` 非対応CLIのみ `brew` に退避する。
- `Brewfile` へ追加する際は、対象行に例外理由コメントを必ず残す。
- `npm` のみで配布されるCLIは、repo 管理の Node を使って `install.sh` から `npm install -g` する。
- 自己更新型CLIは公式インストーラを許容する（例: `curl -fsSL https://claude.ai/install.sh | zsh`）。

## 更新ルール

- `Brewfile` / `aqua.yaml` / `mise.toml` は月1回見直す。
- runtimeの更新はローカルで検証してから、必要分のみ `mise.toml` に反映する。

## 移行メモ

- 旧管理の `volta` / `tfenv` / `gvm` から、runtime管理は `mise` に統一する。
- 新規にruntime管理を追加する場合は、`mise` 以外を増やさない。
- dotfile 管理は `setup.sh` の `ln -sf` 列挙から `chezmoi` に移行済み（issue #1）。初期は symlink 方式だったが、その後 real file + `chezmoi apply` フローに統一した。
