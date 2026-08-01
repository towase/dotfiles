## このリポジトリでの skill 操作
- このリポジトリで skill に対して CRUD 操作を行う場合、対象は `dot_agents/skills/` 配下の skill であること（`~/.claude/skills` やその他の場所ではない）
- `dot_agents/skills/` 配下に変更を入れた後は、`chezmoi diff` で差分を確認すること。差分が今回変更した内容のみであれば `chezmoi apply` を実行して実環境（`~/.claude/` 配下）に反映する。想定外の差分が混じっている場合は apply せず、ユーザーに確認すること

## このリポジトリでの Git 運用
- このリポジトリに限り、`main` ブランチへの直接コミット・プッシュを許可する（`dot_agents/AGENTS.md` の「main / master ブランチに直接コミットしない」ルールをこのリポジトリでは上書きする）
