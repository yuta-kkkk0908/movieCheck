# API ドキュメント

## 基本URL
```
http://localhost:8001/api
```

## エンドポイント

### 映画管理 (`/movies`)

#### GET `/movies/`
全映画取得
```bash
curl http://localhost:8001/api/movies/
```

**パラメータ:**
- `skip` (int, optional): スキップ数 (デフォルト: 0)
- `limit` (int, optional): 取得数 (デフォルト: 100)

#### GET `/movies/{movie_id}`
映画詳細取得
```bash
curl http://localhost:8001/api/movies/1
```

**レスポンス主要フィールド（例）:**
```json
{
  "id": 1,
  "title": "インセプション",
  "genre": "SF",
  "release_date": "2010-07-16T00:00:00",
  "released_year": 2010,
  "director": "クリストファー・ノーラン"
}
```

#### POST `/movies/{movie_id}/refresh-details`
作品詳細を再取得して更新（空値のみ更新 / 強制更新）
```bash
curl -X POST http://localhost:8001/api/movies/1/refresh-details \
  -H "Content-Type: application/json" \
  -d '{"force_update": false}'
```

### 視聴記録 (`/records`)

#### GET `/records/`
全記録取得
```bash
curl http://localhost:8001/api/records/
```

#### POST `/records/`
新規記録作成
```bash
curl -X POST http://localhost:8001/api/records/ \
  -H "Content-Type: application/json" \
  -d '{
    "movie_id": 1,
    "viewed_date": "2024-01-15T10:30:00",
    "viewing_method": "theater",
    "rating": 4.5,
    "mood": "happy",
    "comment": "素晴らしい映画でした"
  }'
```

#### GET `/records/{record_id}`
記録詳細取得
```bash
curl http://localhost:8001/api/records/1
```

#### DELETE `/records/{record_id}`
記録削除
```bash
curl -X DELETE http://localhost:8001/api/records/1
```

### 検索 (`/search`)

#### POST `/search/movies`
映画検索
```bash
curl -X POST http://localhost:8001/api/search/movies \
  -H "Content-Type: application/json" \
  -d '{"query": "インセプション"}'
```

#### POST `/search/register`
映画登録（エージェントが詳細情報を自動取得）
```bash
curl -X POST http://localhost:8001/api/search/register \
  -H "Content-Type: application/json" \
  -d '{
    "title": "インセプション",
    "release_date": "2010-07-16T00:00:00",
    "released_year": 2010,
    "genre": "SF",
    "image_url": "..."
  }'
```

#### POST `/search/sync`
映画.com同期（明示入力 / 保存済み資格情報 / 対話ログインを切替）
```bash
curl -X POST http://localhost:8001/api/search/sync \
  -H "Content-Type: application/json" \
  -d '{
    "email": "example@mail.com",
    "password": "secret",
    "save_credentials": true,
    "use_saved_credentials": true
  }'
```

### 資格情報 (`/credentials`)

#### GET `/credentials/eiga`
保存済み資格情報のメタ情報取得（メールはマスク）
```bash
curl http://localhost:8001/api/credentials/eiga
```

#### PUT `/credentials/eiga`
資格情報の保存/更新/有効化
```bash
curl -X PUT http://localhost:8001/api/credentials/eiga \
  -H "Content-Type: application/json" \
  -d '{
    "email": "example@mail.com",
    "password": "secret",
    "is_active": true
  }'
```

#### DELETE `/credentials/eiga`
保存済み資格情報を削除
```bash
curl -X DELETE http://localhost:8001/api/credentials/eiga
```

### 統計 (`/statistics`)

#### GET `/statistics/overview` （正規）
統一された統計レスポンスを返却
```bash
curl http://localhost:8001/api/statistics/overview
```

#### GET `/statistics/statistics/overview` （互換・非推奨）
`/statistics/overview` と同一レスポンスを返却  
移行期間: 2026-05-31 まで（2026-06-01 に削除予定）
```bash
curl http://localhost:8001/api/statistics/statistics/overview
```

#### GET `/statistics/timeline`
日別の視聴数推移を返却
```bash
curl "http://localhost:8001/api/statistics/timeline?days=30"
```

#### GET `/statistics/mood-recommendations`
気分に応じた高評価作品を返却
```bash
curl "http://localhost:8001/api/statistics/mood-recommendations?mood=happy"
```

## データモデル

### Mood（気分）
- `happy` - 楽しい
- `sad` - 悲しい
- `excited` - 興奮
- `relaxed` - リラックス
- `thoughtful` - 考察的
- `scary` - 怖い
- `romantic` - ロマンティック

### ViewingMethod（視聴方法）
- `theater` - 映画館
- `streaming` - ストリーミング
- `tv` - TV放送
- `dvd` - DVD/Blu-ray
- `other` - その他
