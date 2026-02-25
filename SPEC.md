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
- `cast`（文字列保存。実質 JSON 文字列相当）
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

### 視聴記録

- `GET /records/`: 記録一覧
- `POST /records/`: 記録作成
- `GET /records/{record_id}`: 記録詳細
- `DELETE /records/{record_id}`: 記録削除

### 検索・登録・同期

- `POST /search/movies`: 映画.com 検索
- `POST /search/register`: 映画登録（必要時に詳細スクレイピング）
- `POST /search/sync`: 映画.com 視聴履歴同期
  - `email/password` 省略時は対話ログイン
  - `email/password` 指定時は同期後に認証情報を暗号化保存
  - ログイン用ブラウザが途中で閉じられた場合は同期をキャンセル扱いとする（要実装）
  - キャンセル時はユーザー起因の中断として明示的な結果を返す（要実装）

### 統計

- `GET /statistics/overview`: 総件数や評価分布等を返却
- `GET /statistics/timeline`: 日次視聴推移
- `GET /statistics/mood-recommendations?mood=...`: 気分レコメンド
- 互換/重複実装として `GET /statistics/statistics/overview` も存在

## 7. エージェント/スクレイパー挙動

- `MovieAgent.register_movie()`
  - `external_id` またはタイトルで重複チェック
  - 可能なら `get_movie_details()` で詳細取得して `movies` に保存
- `MovieAgent.sync_from_eiga_com()`
  - ログイン後、ユーザー視聴ページを巡回し映画一覧取得
  - 作品ごとに重複判定後 `movies` を追加
  - 視聴日単位で `records` 重複判定し、未登録のみ追加
  - 認証情報が入力された場合のみ暗号化保存

### `/authorize/done` 対応

- `a.univLink` を優先クリック
- 失敗時は XPath (`/login/oauth/gid/` 含むリンク) を試行
- リダイレクト URL から `/user/{id}/` 抽出し `/user/{id}/movie/` へ遷移
- 取れない場合はページ内の user リンク探索でフォールバック

## 8. フロントエンド挙動

- タブ構成: ダッシュボード / トップ / 映画検索 / 記録一覧
- 同期ボタン（ヘッダ）から同期モーダルを開き対話ログイン同期を実行
- 映画検索結果から「登録して記録」で記録作成モーダルを表示
- 記録一覧は閲覧中心（編集 UI なし、削除 UI なし）

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
- 現状、`backend/` にはテストコードが未配置のため `pytest` 実行時に 0 件または失敗となる可能性がある。
- フロントエンドは `react-scripts test` を使用する。
- 実行には Python / Node.js のローカルインストールが必要。

## 10. 実装後に判明しやすいリスク

- 映画.com 側 DOM 変更によるスクレイパー破損。
- Selenium/ChromeDriver バージョン差異による環境依存不具合。
- 対話ログイン中の想定外画面（2段階認証など）での待機ハング。
- 同期中断時のトランザクション rollback 漏れ。
- 同一映画判定の表記揺れ（全角/半角・副題差分）による重複登録。
