# 導入元と配置

yomiyasu は https://github.com/nanaism/yomiyasu の `skills/yomiyasu/`（main、commit 41e5aec、スキルのバージョン 2.4.0）を 2026-10-29 に取り込んだもの。`LICENSE` と `UNICODE-LICENSE.txt` は上流の `skills/yomiyasu/` に入っているものをそのまま置いている。上流リポジトリ直下の同名ファイルと同じ内容である。

上流のスキル本文、参照資料、スクリプトは変更せずに置く。dotfiles 側で足したファイルは、この `INSTALLATION.md` だけ。上流の `.codex-plugin/` だけは、ソースでは `dot_codex-plugin/` という名前で置いている。chezmoi はソース内のドット始まりのファイルを配置しないためで、配置先では上流と同じ `.codex-plugin/plugin.json` になる。

## 配置先と呼び出し名

chezmoi がこのディレクトリを `~/.agents/skills/yomiyasu/` に配置する。Codex はこのディレクトリを直接読み、Claude Code は `~/.claude/skills`（`~/.agents/skills` への symlink）から同じディレクトリを読む。

スキルの名前はホストで異なる。Claude Code では `yomiyasu`（`/yomiyasu`）。Codex では同梱の `.codex-plugin/plugin.json` により `yomiyasu:yomiyasu`（`$yomiyasu:yomiyasu`）になり、`$yomiyasu` とだけ書くとスキルの指示は読み込まれない。

成果物の文章を毎回 yomiyasu に通す指示は、dotfiles の `dot_agents/AGENTS.md` にある「成果物の文章チェック」の節で管理する。`dot_claude/CLAUDE.md.tmpl` と `dot_codex/AGENTS.md.tmpl` が同じファイルを include し、`~/.claude/CLAUDE.md` と `~/.codex/AGENTS.md` を生成する。

任意のフック `scripts/yomiyasu_hook.py` は入れていない。登録した原稿の検査漏れを返答の終わりに止めたいときは、`python3 -B scripts/yomiyasu_hook.py --print-config claude-code`（Codex は `codex`）が出す JSON を、`~/.claude/settings.json` か対象プロジェクトの `.codex/hooks.json` に自分で貼る。上流は `~/.claude/settings.json` と `~/.codex/hooks.json` に置く形を確かめていない。

## 更新のしかた

`chezmoi apply` はリポジトリ内のファイルを配置するだけで、GitHub からのダウンロードや最新版への更新はしない。

上流を更新するときは、次の順で進める。2 つのライセンスを含む上流の `skills/yomiyasu/` の中身をこのディレクトリへ取り込む（`.codex-plugin/` は `dot_codex-plugin/` に入れる）。`chezmoi diff` に今回の変更だけが出ることを確認したうえで `chezmoi apply` し、無関係な差分があればリポジトリの `AGENTS.md` に従って確認を取る。apply 後に `diff -r <上流の skills/yomiyasu> ~/.agents/skills/yomiyasu` の差分が `INSTALLATION.md` だけであることを確かめ、このファイルの取得日、commit、バージョンを書き換える。配置先に上流以外のファイル（古い手動インストールの残りなど）が残っていても chezmoi は消さないため、その場合は配置先を消してから apply する。`scripts/__pycache__/` はスクリプトの実行時にできるキャッシュなので、差分に出たら消してよい。
