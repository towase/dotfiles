# 導入元と配置

yomiyasu は https://github.com/nanaism/yomiyasu の `skills/yomiyasu/`（タグ v3.1.0、commit db78b9b、スキルのバージョン 3.1.0）を 2026-11-13 に取り込んだもの。`LICENSE` と `UNICODE-LICENSE.txt` は上流の `skills/yomiyasu/` に入っているものをそのまま置いている。上流リポジトリ直下の同名ファイルと同じ内容である。

上流のスキル本文、参照資料、スクリプトは変更せずに置く。dotfiles 側で足したファイルは、この `INSTALLATION.md` だけ。

## 配置先と呼び出し名

chezmoi がこのディレクトリを `~/.agents/skills/yomiyasu/` に配置する。Codex はこのディレクトリを直接読み、Claude Code は `~/.claude/skills`（`~/.agents/skills` への symlink）から同じディレクトリを読む。

スキルの名前は Claude Code でも Codex でも `yomiyasu` で、Claude Code では `/yomiyasu`、Codex では `$yomiyasu` と書いて呼ぶ。Codex はスキルのフォルダから上のフォルダへ順にプラグインの設定を探し、最初に見つけた設定の名前をスキルの名前の先頭に付ける。3.0.1 までは上流がスキルのフォルダに `.codex-plugin/plugin.json` を置いていたため、Codex での名前は `yomiyasu:yomiyasu` だった。3.1.0 で上流がこのファイルを消したので、Codex でも `yomiyasu` になった。配置先に `.codex-plugin/` が残っていたり、上のフォルダにプラグインの設定があったりすると、名前は `yomiyasu` にならない。

成果物の文章を毎回 yomiyasu に通す指示は、dotfiles の `dot_agents/AGENTS.md` にある「成果物の文章チェック」の節で管理する。`dot_claude/CLAUDE.md.tmpl` と `dot_codex/AGENTS.md.tmpl` が同じファイルを include し、`~/.claude/CLAUDE.md` と `~/.codex/AGENTS.md` を生成する。

任意のフック `scripts/yomiyasu_hook.py` は入れていない。登録した原稿の検査漏れを返答の終わりに止めたいときは、`python3 -B scripts/yomiyasu_hook.py --print-config claude-code`（Codex は `codex`）が出す JSON を、`~/.claude/settings.json` か対象プロジェクトの `.codex/hooks.json` に自分で貼る。上流は `~/.claude/settings.json` と `~/.codex/hooks.json` に置く形を確かめていない。

## 更新のしかた

`chezmoi apply` はリポジトリ内のファイルを配置するだけで、GitHub からのダウンロードや最新版への更新はしない。

上流を更新するときは、次の順で進める。2 つのライセンスを含む上流の `skills/yomiyasu/` の中身をこのディレクトリへ取り込む。`rsync -a --delete --exclude INSTALLATION.md <上流の skills/yomiyasu>/ dot_agents/skills/yomiyasu/` で取り込むと、上流で消えたファイルもこのディレクトリから消える。`chezmoi diff` に今回の変更だけが出ることを確認したうえで `chezmoi apply` し、無関係な差分があればリポジトリの `AGENTS.md` に従って確認を取る。apply 後に `diff -r <上流の skills/yomiyasu> ~/.agents/skills/yomiyasu` の差分が `INSTALLATION.md` だけであることを確かめ、このファイルの取得日、commit、バージョンを書き換える。

上流で消えたファイルや古い手動インストールの残りが配置先にあっても、chezmoi は消さない。その場合は配置先を消してから apply する。配置先を消すと、`chezmoi apply` は配置先が変わったことの確認を求める。端末で答えられないときは `chezmoi apply --force ~/.agents/skills/yomiyasu` で配置する。3.0.1 以前を配置していたマシンでは `.codex-plugin/` が残るので、3.1.0 以降を初めて apply する前に配置先を消す。`scripts/__pycache__/` はスクリプトの実行時にできるキャッシュなので、差分に出たら消してよい。
