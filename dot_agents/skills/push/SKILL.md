---
name: push
description: 現在のブランチを origin に push する。上流が未設定なら `-u origin <branch>` で初回 push する。force push（`--force` / `--force-with-lease`）は本 skill では行わない。「/push」と明示的に指示されたとき、または本 skill が呼び出されたときに使用する。
disable-model-invocation: true
allowed-tools: Bash
---

# push

現在のブランチを `origin` に push する。

## 前提

- ユーザー本人のリポジトリ、または [[work-on-main]] / プロジェクト固有ルールで push が許可されているリポジトリでのみ呼ばれる想定。
- CI 監視（`gh run watch` 等）はこの skill では行わない。必要なら [[verify]] / [[loop]] / [[review-resolve-loop]] を併用する。

## 手順

### 1. 状態確認

```sh
git status
git rev-parse --abbrev-ref HEAD
git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null
```

- 未 commit の変更が残っていても push 自体は阻害しない（あくまで warning として伝える）。
- 上流ブランチが取得できなければ「初回 push」と扱う。

### 2. push

- 上流あり: `git push`
- 上流なし: `git push -u origin <current-branch>`

ブランチが main / master で、リポジトリ側のルールが直接 push を禁止しているなら、ここで止めてユーザーに確認する。

### 3. 確認

push 後の `git status`、push したコミットの短い SHA、リモートのブランチ名を 1 行で報告する。

## やらないこと

- `git push --force` / `git push --force-with-lease`（force push を行いたい場合は、この skill ではなくユーザーから明示指示を受けて別途実行する）
- 新しいリモートの追加・URL 設定変更
- push 後の CI 結果の監視
- リモートに未存在のブランチを勝手に作る判断（`-u` 設定は初回 push の通常動作のみ）
