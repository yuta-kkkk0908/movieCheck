# 同期ワークフローテスト方針

更新日: 2026-02-26

## 対象

- `MovieAgent.sync_from_eiga_com_with_options()`

## モック方針

- 外部依存（Selenium/映画.com 通信）は `FakeScraper` で置換する。
- DB は `sqlite://` + `StaticPool` のインメモリDBを使い、テストごとにスキーマを作り直す。
- `monkeypatch` で以下を差し替える。
  - `agent.tasks.movie_agent.MovieComScraper`
  - `agent.tasks.movie_agent.SessionLocal`

## 検証シナリオ

1. 重複登録防止
   - 同期を2回連続実行しても `Movie=1`, `Record=1` を維持する。
2. 例外時 rollback
   - 取得処理で例外発生時に `success=False` となり、DBに中途データを残さない。
3. 再実行安全性
   - 失敗後に再実行して成功した場合、整合性が保たれた状態で登録される。

## 実行コマンド

- ルートから: `bash scripts/test-backend.sh`
- 直接実行:
  - `cd backend`
  - `python -m pytest -q tests/test_sync_workflow.py`
