"""
バックエンド初期化ファイル
"""
import sys
import os
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.db.database import create_tables

# プロジェクトルートをPYTHONPATHに追加して、トップレベルの `agent` パッケージをimport可能にする
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.append(ROOT)

def create_app():
    """FastAPI アプリケーション生成"""
    app = FastAPI(title="Movie App API", version="1.0.0")
    
    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # DB初期化
    @app.on_event("startup")
    async def startup():
        create_tables()
    
    # ルート登録
    from app.api import movies, records, search, statistics
    app.include_router(movies.router, prefix="/api/movies", tags=["movies"])
    app.include_router(records.router, prefix="/api/records", tags=["records"])
    app.include_router(search.router, prefix="/api/search", tags=["search"])
    app.include_router(statistics.router, prefix="/api/statistics", tags=["statistics"])
    
    return app

if __name__ == "__main__":
    import uvicorn
    app = create_app()
    # ポート 8000 が使用中の場合は 8001 を試す
    uvicorn.run(app, host="0.0.0.0", port=8001)
