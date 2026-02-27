"""
映画検索・スクレイピング API
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Movie
from agent.tasks.movie_agent import MovieAgent
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

router = APIRouter()

class SearchQuery(BaseModel):
    query: str

class SearchResult(BaseModel):
    title: str
    release_date: Optional[datetime] = None
    released_year: Optional[int] = None
    genre: Optional[str] = None
    image_url: Optional[str] = None
    movie_url: Optional[str] = None
    external_id: Optional[str] = None

class SyncRequest(BaseModel):
    email: Optional[str] = None  # オプション：対話型ログイン時はNone
    password: Optional[str] = None  # オプション：対話型ログイン時はNone
    save_credentials: bool = False
    use_saved_credentials: bool = True

class SyncResponse(BaseModel):
    success: bool
    cancelled: bool = False
    message: str
    added: int
    existing: int
    errors: int
    can_fallback_to_interactive: bool = False

@router.post("/movies", response_model=List[SearchResult])
async def search_movies(search: SearchQuery, db: Session = Depends(get_db)):
    """
    映画検索（ネットから取得）
    """
    if not search.query:
        return []
    
    try:
        results = MovieAgent.search_movies(search.query)
        return [SearchResult(**r) for r in results]
    except Exception as e:
        print(f"検索エラー: {e}")
        return []

@router.post("/register")
async def register_movie(movie: SearchResult, db: Session = Depends(get_db)):
    """
    映画登録（エージェントが詳細情報を自動取得）
    """
    try:
        movie_obj = MovieAgent.register_movie(
            movie.dict(),
            movie.movie_url or ""
        )
        
        if movie_obj:
            return {
                "success": True,
                "message": "映画を登録しました",
                "movie_id": movie_obj.id
            }
        else:
            return {
                "success": False,
                "message": "映画の登録に失敗しました"
            }
    except Exception as e:
        print(f"登録エラー: {e}")
        return {
            "success": False,
            "message": f"登録中にエラーが発生しました: {str(e)}"
        }

@router.post("/sync", response_model=SyncResponse)
async def sync_eiga_com(request: SyncRequest, background_tasks: BackgroundTasks):
    """
    映画.comから視聴履歴を同期
    
    Args:
        email: メールアドレス（オプション：対話型ログイン用）
        password: パスワード（オプション：対話型ログイン用）
    
    Returns:
        同期結果
    """
    try:
        result = MovieAgent.sync_from_eiga_com_with_options(
            email=request.email,
            password=request.password,
            save_credentials=request.save_credentials,
            use_saved_credentials=request.use_saved_credentials
        )
        return SyncResponse(**result)
    except Exception as e:
        print(f"同期エラー: {e}")
        import traceback
        traceback.print_exc()
        return SyncResponse(
            success=False,
            cancelled=False,
            message=f"同期中にエラーが発生しました: {str(e)}",
            added=0,
            existing=0,
            errors=1,
            can_fallback_to_interactive=False
        )
