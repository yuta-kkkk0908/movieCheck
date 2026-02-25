# Changelog

## 2026-02-25

- `AGENT_SETTINGS.md` を追加し、運用ルール（最小差分修正、タスク表記ゆれ解釈、履歴記録、仕様更新同期、再開プロンプト）を定義。
- `SPEC.md` を追加し、仕様ドキュメント運用ルールを明文化。
- `TASKS.md` に運用ルール連携セクションを追加。
- `SPEC.md` に `CURRENT_SPEC.md` の内容を統合し、単一仕様書として整理。
- ルート `Makefile` を追加し、起動・一括起動・分割起動・テスト実行の短縮コマンドを追加。
- `scripts/*.sh`（起動・テスト）を追加し、`make` 非依存の短縮コマンドを整備。
- `frontend/package.json` に `test` スクリプトを追加。
- `CURRENT_SPEC.md` を削除し、仕様書を `SPEC.md` に統合。
- ルート `package.json` を追加し、`npm run dev` / `npm run backend` / `npm run frontend` / `npm test` などの短縮コマンドを追加。
- `scripts/*.ps1` を追加し、PowerShell から直接実行できる起動・テストコマンドを追加。
- 同期中にログインブラウザを閉じた場合の「同期キャンセル」要件を `SPEC.md` と `TASKS.md` に追加。
- `TASKS.md` を全面改訂し、各タスクに目的・実装仕様・DoD・失敗時挙動・優先順を定義。
- 実装後に判明しやすいリスクを `SPEC.md` に追記。
