# Movie App 仕様書

更新日: 2026-02-25

## 1. 本書の位置づけ

- 本ファイルを仕様の正本とする。
- 仕様変更時は `SPEC.md` と `TASKS.md` を同時更新する。

## 2. 運用仕様（ドキュメント更新ルール）

1. 仕様に関する変更は `SPEC.md` と `TASKS.md` の両方に記載する。
2. 実装変更を伴う場合は `CHANGELOG.md` に履歴を残す。
3. 修正は必要箇所のみを対象とし、無関係な一括修正を行わない。
4. タスク参照は表記ゆれを許容する。
   - 例: `タスク1`, `タスク１`, `#1`, `Task 1`

## 3. 目的

- 映画視聴記録をローカル SQLite に保存するデスクトップ向けアプリ
- 映画.com からの検索・詳細取得・視聴履歴同期をサポート
- フロントは React（Electron 起動想定）、バックエンドは FastAPI

## 4. システム構成

- フロントエンド: React + Ant Design + Axios
- デスクトップ起動: Electron（`frontend/public/electron.js`）
- バックエンド: FastAPI + SQLAlchemy + SQLite
- スクレイピング: Selenium + BeautifulSoup + requests

## 5. データモデル（SQLite）

### `movies`

- `id` (PK)
- `title` (必須)
- `genre`
- `released_year`
- `director`
- `cast`（JSON配列を文字列として保存）
- `synopsis`
- `image_url`
- `external_id`（ユニーク）
- `created_at`, `updated_at`

### `records`

- `id` (PK)
- `movie_id` (FK -> movies.id)
- `viewed_date` (必須)
- `viewing_method` (Enum: `theater|streaming|tv|dvd|other`)
- `rating` (float)
- `mood` (Enum: `happy|sad|excited|relaxed|thoughtful|scary|romantic`)
- `comment`
- `created_at`, `updated_at`

### `eiga_credentials`

- `id` (PK)
- `email`（ユニーク）
- `password_encrypted`（Fernet 暗号化）
- `is_active`
- `last_sync`
- `created_at`, `updated_at`

## 6. バックエンド API

ベース: `http://localhost:8001/api`

### 映画

- `GET /movies/`: 映画一覧
- `GET /movies/{movie_id}`: 映画詳細
- `POST /movies/{movie_id}/refresh-details`: 作品詳細再取得
  - `force_update=false`: 空値のみ更新
  - `force_update=true`: 強制上書き

### 視聴記録

- `GET /records/`: 記録一覧
- `POST /records/`: 記録作成
- `GET /records/{record_id}`: 記録詳細
- `PATCH /records/{record_id}`: 記録更新
  - 更新対象: `viewed_date`, `viewing_method`, `rating`, `mood`, `comment`
  - バリデーションエラー時は `422`（項目別メッセージ）
- `DELETE /records/{record_id}`: 記録削除

### 検索・登録・同期

- `POST /search/movies`: 映画.com 検索
- `POST /search/register`: 映画登録（必要時に詳細スクレイピング）
- `POST /search/sync`: 映画.com 視聴履歴同期
  - `email/password` 省略時は対話ログイン
  - `save_credentials=true` かつ `email/password` 指定時のみ同期後に認証情報を暗号化保存
  - `use_saved_credentials=true` かつ明示入力なしの場合は保存済み有効資格情報を優先利用
  - 利用優先順: 明示入力 → 保存済み有効資格情報 → 対話ログイン
  - ログイン用ブラウザが途中で閉じられた場合は同期をキャンセル扱いとする
  - キャンセル時は `success=false` かつ `cancelled=true` を返す
  - 保存済み資格情報の復号/認証失敗時は `can_fallback_to_interactive=true` を返す

### 資格情報

- `GET /credentials/eiga`: 保存済み有効資格情報のメタ情報取得（メールはマスク、平文パスワード非返却）
- `PUT /credentials/eiga`: 資格情報の保存/更新/有効化
- `DELETE /credentials/eiga`: 保存済み資格情報を削除

### 統計

- `GET /statistics/overview`: 総件数や評価分布等を返却
- `GET /statistics/timeline`: 日次視聴推移
- `GET /statistics/mood-recommendations?mood=...`: 気分レコメンド
- 互換エンドポイントとして `GET /statistics/statistics/overview` も同一レスポンスを返す（非推奨）
  - 移行期間: 2026-02-26 から 2026-05-31
  - 削除予定日: 2026-06-01
- `GET /statistics/overview` のレスポンスキー:
  - `total_movies`, `total_records`, `recent_90_days`, `top_genre`
  - `average_rating`, `genre_stats`, `mood_stats`, `viewing_method_stats`
  - `rating_distribution`, `recent_records`

## 7. エージェント/スクレイパー挙動

- `MovieAgent.register_movie()`
  - `external_id` またはタイトルで重複チェック
  - 可能なら `get_movie_details()` で詳細取得して `movies` に保存
  - `cast` は JSON文字列形式で保存
- `MovieAgent.sync_from_eiga_com()`
  - ログイン後、ユーザー視聴ページを巡回し映画一覧取得
  - 作品ごとに重複判定後 `movies` を追加
  - 視聴日単位で `records` 重複判定し、未登録のみ追加
  - 監督は一覧要素 `<p class="sub">` から先に抽出し、空の場合のみ詳細ページ取得で補完
  - 公開年は一覧情報（年/公開日）を優先し、必要時に詳細ページ取得で補完
  - 認証情報が入力された場合のみ暗号化保存
  - `cast` は JSON文字列形式で保存

### `/authorize/done` 対応

- `a.univLink` を優先クリック
- 失敗時は XPath (`/login/oauth/gid/` 含むリンク) を試行
- リダイレクト URL から `/user/{id}/` 抽出し `/user/{id}/movie/` へ遷移
- 取れない場合はページ内の user リンク探索でフォールバック

## 8. フロントエンド挙動

- タブ構成: ダッシュボード / トップ / 映画検索 / 記録一覧
- 同期ボタン（ヘッダ）から同期モーダルを開き対話ログイン同期を実行
- ヘッダにミニ検索入力 + 検索ボタンを配置し、実行時は「映画検索」タブへ遷移して既存の登録フローへ接続する
- 映画検索結果から「登録して記録」で記録作成モーダルを表示
- 記録一覧で編集モーダル・削除確認ダイアログから更新/削除を実行できる
- 記録一覧で映画の公開年・監督を表示する
- 記録一覧で映画ごとの「作品情報取得」（空値更新）/「強制更新」実行ができる

## 9. 開発実行コマンド（短縮）

依存が少ない `scripts/*.sh` を基本コマンドとする。  
(`Makefile` も補助として利用可能)

Windows PowerShell からは、ルート `package.json` の `npm run` エイリアスを優先利用する。

### npm run（PowerShell向け）

- バックエンドのみ: `npm run backend`
- フロントエンドのみ: `npm run frontend`
- 一括起動（同一ターミナル）: `npm run dev`
- 一括起動（別ターミナル）: `npm run dev:split`
- テスト一括: `npm test`
- テスト個別:
  - `npm run test:backend`
  - `npm run test:frontend`

### 起動

- バックエンドのみ: `bash scripts/dev-backend.sh`
- フロントエンドのみ: `bash scripts/dev-frontend.sh`
- バックエンド + フロント同時起動（同一ターミナル）: `bash scripts/dev-both.sh`
- 別ターミナル運用:
  - Terminal A: `bash scripts/dev-backend.sh`
  - Terminal B: `bash scripts/dev-frontend.sh`

### テスト実行

- バックエンド: `bash scripts/test-backend.sh`
- フロントエンド: `bash scripts/test-frontend.sh`
- 一括: `bash scripts/test-all.sh`

備考:
- `backend/tests/test_sync_workflow.py` で同期ワークフロー（重複防止/rollback/再実行安全性）を自動テスト可能。
- フロントエンドは `react-scripts test` を使用する。
- 実行には Python / Node.js のローカルインストールが必要。
- 手動の同期検証チェックリストは `docs/SYNC_CHECKLIST.md` を参照。
- 外部依存モック方針と再現手順は `docs/SYNC_TEST_STRATEGY.md` を参照。
- OAuthログイン失敗時の原因分析と成功パターンは `docs/OAUTH_LOGIN_PLAYBOOK.md` を参照。

## 10. 実装後に判明しやすいリスク

- 映画.com 側 DOM 変更によるスクレイパー破損。
- Selenium/ChromeDriver バージョン差異による環境依存不具合。
- 対話ログイン中の想定外画面（2段階認証など）での待機ハング。
- 同期中断時のトランザクション rollback 漏れ。
- 同一映画判定の表記揺れ（全角/半角・副題差分）による重複登録。
