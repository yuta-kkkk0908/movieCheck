# API ドキュメント

## 基本URL
```
http://localhost:8000/api
```

## エンドポイント

### 映画管理 (`/movies`)

#### GET `/movies/`
全映画取得
```bash
curl http://localhost:8000/api/movies/
```

**パラメータ:**
- `skip` (int, optional): スキップ数 (デフォルト: 0)
- `limit` (int, optional): 取得数 (デフォルト: 100)

#### GET `/movies/{movie_id}`
映画詳細取得
```bash
curl http://localhost:8000/api/movies/1
```

### 視聴記録 (`/records`)

#### GET `/records/`
全記録取得
```bash
curl http://localhost:8000/api/records/
```

#### POST `/records/`
新規記録作成
```bash
curl -X POST http://localhost:8000/api/records/ \
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
curl http://localhost:8000/api/records/1
```

#### DELETE `/records/{record_id}`
記録削除
```bash
curl -X DELETE http://localhost:8000/api/records/1
```

### 検索 (`/search`)

#### POST `/search/movies`
映画検索
```bash
curl -X POST http://localhost:8000/api/search/movies \
  -H "Content-Type: application/json" \
  -d '{"query": "インセプション"}'
```

#### POST `/search/register`
映画登録（エージェントが詳細情報を自動取得）
```bash
curl -X POST http://localhost:8000/api/search/register \
  -H "Content-Type: application/json" \
  -d '{
    "title": "インセプション",
    "released_year": 2010,
    "genre": "SF",
    "image_url": "..."
  }'
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
