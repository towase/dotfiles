---
name: work-on-main
description: 自分がオーナーの GitHub リポジトリに限り、main / master ブランチ上で直接実装・commit・push することを許可する。CLAUDE.md の「main に直接コミット禁止」「作業時はフィーチャーブランチを切る」ルールをこのセッションに限り上書きする。「work-on-main」「main で作業」「main で進める」と明示的に指示されたとき、またはユーザーが本 skill を呼び出したときに使用する。
---

# work-on-main

このスキルが呼び出されたセッションでは、以下を許可する。

- 現在のブランチが `main` / `master` のまま、新しいフィーチャーブランチを作成せずに作業を進める
- `main` / `master` への直接 commit
- `main` / `master` からの直接 push（`origin main` / `origin master` への push）

CLAUDE.md（ユーザーグローバル / プロジェクトの両方）の以下ルールは、このセッション中のみ上書きされる:

- 「作業開始時に現在のブランチが main または master の場合、必ず新しいフィーチャーブランチを作成してから作業を始めること」
- 「main / master ブランチに直接コミットしないこと」

## 前提条件: オーナーシップ確認

直 commit / push に進む前に、対象リポジトリが「ユーザー本人がオーナー」であることを確認する。

判定方法: `gh repo view --json owner` で GitHub 上のオーナーを確認する。

```sh
gh repo view --json owner
```

判定基準:

- `owner.login == "towase"` → オーナー確認 OK、直 commit / push 可
- それ以外（組織リポジトリ、他人のリポジトリ、admin 権限を持つだけの場合も含む） → **本スキルは適用しない**。通常の CLAUDE.md ルールに従い、フィーチャーブランチを切って PR 経由で作業する
- `gh` 未認証 / GitHub 上に存在しないリポジトリ / コマンド失敗 → ユーザーに確認する（勝手にフォールバック判定をしない）

判定結果を最初のターンで短く宣言してから作業に入ること（例: 「owner.login=towase を確認、main 上で進めます」）。

## 運用上の注意

- force push（`git push --force` / `--force-with-lease`）は、このスキルが有効でもユーザーの明示的な許可なしに実行しない
- commit は「ユーザーが commit を作成するよう明示的に依頼したとき」のみ作成するという通常ルールは維持する（このスキルはブランチ制約のみを緩和する）
- push 後に CI が落ちた場合は、main が壊れた状態になるため即座にユーザーに報告する
