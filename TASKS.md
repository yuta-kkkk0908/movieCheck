# Movie App - タスク一覧（2026-02-25 改訂）

## 運用ルール（仕様・履歴）

- 仕様の正本は `SPEC.md` とする。
- 仕様に関する変更は `SPEC.md` と本ファイルの両方を更新する。
- 実装変更を伴う修正は `CHANGELOG.md` に履歴を追記する。
- タスク指定は表記ゆれを許容して解釈する（例: `タスク1`, `タスク１`, `#1`, `Task 1`）。
- 開発用の短縮コマンドは `scripts/*.sh` を正とし、PowerShell では `npm run` を優先する。

## 状態凡例

- `DONE`: 実装済み
- `PARTIAL`: 一部実装済み
- `TODO`: 未実装

## タスク詳細

### 1. `DONE` Improve /authorize/done navigation (univLink handling)

- 目的:
  - `/authorize/done` から確実に `/user/{user_id}/movie/` へ遷移させる。
- 実装仕様:
  - `a.univLink` を優先クリック。
  - 失敗時は XPath でフォールバック。
  - URL から `user_id` 抽出。抽出不能時はページ内リンク探索。
- DoD:
  - 対話ログイン後、3パターン（通常/フォールバック/リンク探索）で到達確認できる。
  - 到達失敗時にログで原因が判別できる。

### 2. `DONE` Save credentials & auto-login

- 目的:
  - 認証情報保存と次回以降の自動ログインを可能にする。
- 実装:
  - 同期モーダルに「保存して次回自動ログイン」チェックを追加。
  - 保存済み認証情報の利用優先順を実装:
    1) 明示入力
    2) 保存済み有効資格情報
    3) 対話ログイン
  - 資格情報管理 API（取得/更新/削除/有効化）を追加。
- DoD:
  - 保存ONで同期成功後、再同期時に入力なしでログインできる。
  - 保存OFF時は資格情報が更新されない。
  - 削除後は自動ログインされない。
- 失敗時挙動:
  - 復号失敗・認証失敗時は自動ログインを中断し、対話ログインへの切替可否を返す。

### 3. `DONE` Show search next to sync button

- 目的:
  - ヘッダから即時検索できる導線を追加する。
- 実装仕様:
  - 同期ボタン横にミニ検索入力 + 実行ボタン。
  - 結果は既存 `登録して記録` フローへ接続。
- DoD:
  - ヘッダ検索から登録・記録作成まで完走できる。
  - 既存の「映画検索」タブ機能と競合しない。

### 4. `DONE` Allow editing/deleting records

- 目的:
  - 記録の編集・削除を UI/API 両面で提供する。
- 実装:
  - `PATCH /api/records/{id}` を追加。
  - 編集対象: `viewed_date`, `viewing_method`, `rating`, `mood`, `comment`。
  - 削除 UI（確認ダイアログ付き）を追加。
- DoD:
  - 一覧画面で編集保存後、再読み込みしても値が保持される。
  - 削除実行後、一覧から即時反映される。
- バリデーション:
  - `rating`: 0.0-5.0
  - `viewing_method`/`mood`: enum 制約
  - `viewed_date`: ISO 8601

### 5. `DONE` Add fetch details button (year & cast)

- 目的:
  - 既存映画の詳細情報を後追い取得できるようにする。
- 実装:
  - 記録一覧の映画ごとに「作品情報取得」「強制更新」ボタンを追加。
  - API `POST /api/movies/{id}/refresh-details`（新規）で `get_movie_details()` 呼び出し。
- DoD:
  - 年・キャスト・監督・あらすじの更新結果が UI に反映される。
- 上書きルール:
  - 空値は上書き許可。
  - 既存値がある場合の上書き可否をオプション化（強制更新フラグ）。

### 6. `DONE` Ensure scraper captures director

- 目的:
  - 同期時点で監督欠損を減らす。
- 実装:
  - リスト要素 `<p class="sub">` から監督名抽出を追加。
  - 抽出結果が空の場合のみ詳細ページ補完。
- DoD:
  - 監督欠損率が同期データで下がる（確認ログまたは件数比較）。

### 7. `DONE` Test complete scrape workflow

- 目的:
  - フル同期の品質確認を手順化する。
- 実装仕様:
  - 手動確認チェックリストを `docs/` に追加。
  - 主要シナリオ: 初回同期、再同期、重複、途中失敗、復帰。
- 実装:
  - `docs/SYNC_CHECKLIST.md` を追加。
  - 同期の主要シナリオごとの手順・期待結果・判定基準を明文化。
- DoD:
  - チェックリストに従い誰でも同じ検証ができる。

### 8. `DONE` Consolidate statistics API design

- 目的:
  - 重複実装の統計 API を一本化して保守性を上げる。
- 実装仕様:
  - `GET /api/statistics/overview` のレスポンス仕様を確定。
  - 互換エンドポイントの廃止時期と移行期間を決める。
- 実装:
  - 正規エンドポイントを `GET /api/statistics/overview` に統一。
  - 互換エンドポイント `GET /api/statistics/statistics/overview` は同一レスポンスを返す非推奨経路として維持。
  - 移行期間を 2026-05-31 までとし、2026-06-01 以降に削除予定。
- DoD:
  - フロントで使用する全キーが統一 API で取得できる。
  - 旧経路削除後も画面が壊れない。

### 9. `DONE` Credential lifecycle management

- 目的:
  - 資格情報の運用安全性を担保する。
- 実装仕様:
  - `GET/PUT/DELETE /api/credentials/eiga` を追加。
  - ログ/レスポンスへ平文資格情報を出力しない。
- DoD:
  - 保存・更新・削除の各操作が UI 経由で完了できる。
  - 削除後の再同期は対話ログインにフォールバックする。

### 10. `DONE` Record update API and validation

- 目的:
  - 記録更新 API の入力品質を保証する。
- 実装仕様:
  - `PATCH /api/records/{id}` を正式化。
  - バリデーションエラー時は `422` で項目別メッセージ返却。
- DoD:
  - 正常系で更新後の再読み込み反映を確認できる。
  - 異常系（型不正/範囲外/enum不正）で `422` と項目別メッセージを返す。

### 11. `DONE` Movie detail refresh API

- 目的:
  - 詳細再取得ロジックを API として独立させる。
- 実装仕様:
  - 単体更新 API + 将来の一括更新 API を見据えた設計。
  - 上書き方針（空値のみ/強制上書き）を明示。
- DoD:
  - 既存データに対して再取得実行しても整合性が壊れない。

### 12. `DONE` Cast data type normalization

- 目的:
  - `movies.cast` を JSON 配列として正規化する。
- 実装仕様:
  - DB スキーマ変更（TEXT + JSON文字列運用継続 or JSON型相当）を定義。
  - 移行スクリプト作成（既存 `str(list)` 形式を配列へ変換）。
- DoD:
  - 旧データを移行後に読める。
  - 新規保存は統一形式で保存される。

### 13. `DONE` Scrape workflow tests

- 目的:
  - 同期処理の回帰を自動検知する。
- 実装仕様:
  - 結合テスト: 重複登録防止、例外発生時 rollback、再実行の安全性。
  - 外部依存をモック化する方針を明記。
- DoD:
  - CI なしでもローカルで再現可能なテスト手順がある。

### 14. `DONE` Cancel sync when login browser is closed

- 目的:
  - ユーザーがログインブラウザを閉じた場合に同期を安全に中断する。
- 実装仕様:
  - ドライバ切断・ウィンドウクローズを検出。
  - 中断時はトランザクションを rollback。
  - API は `success=false` と `cancelled=true` を返す。
- DoD:
  - ログイン前/同期中の両ケースで中断が検知できる。
  - DB に中途半端なデータが残らない。

## 実装後に判明しやすいリスク（事前に把握）

- 映画.com 側 DOM 変更でスクレイパーが突然壊れる。
- Selenium/ブラウザドライバ差異（OS・Chrome版）で再現性が崩れる。
- 対話ログイン中の想定外遷移（2段階認証・年齢確認）で待機ロジックがハングする。
- 同期中断時の rollback 漏れ（flush済みデータ残り）。
- 文字コード/表記揺れで同一映画の重複判定が漏れる。

## 次の優先実装順

1. 未着手タスクなし（本一覧の 1-14 は `DONE`）
2. 追加要件は本ファイル末尾へ追記して管理する
