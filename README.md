# 映画視聴管理アプリケーション

映画の視聴履歴を記録し、ローカルDBで管理。ネット接続時に映画情報を自動取得するエージェント型デスクトップアプリケーション。

## 機能
- 📽️ **映画検索** - ネットから映画情報を検索
- 💾 **ローカル保存** - 視聴履歴をSQLiteで管理
- 🤖 **自動エージェント** - 登録時に映画情報を自動取得
- 🏠 **気分レコメンド** - 気分に応じたおすすめ表示
- 🎬 **関連作品表示** - 出演者・監督別の関連作品

## プロジェクト構成
```
movie-app/
├─ backend/          FastAPI + SQLite + スクレイピング
├─ frontend/         Electron + React
├─ agent/            タスク処理・キューイング（Celery）
└─ docs/             ドキュメント
```

## セットアップ

### 必要環境
- Python 3.9+
- Node.js 16+

### バックエンド起動
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### フロントエンド起動
```bash
cd frontend
npm install
npm start
```

## DBについて
SQLiteはローカルに自動生成されます。初期化は不要です。
- 保存先: `backend/instance/movies.db`
