"""
映画管理 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Movie
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

class MovieResponse(BaseModel):
    id: int
    title: str
    genre: Optional[str]
    released_year: Optional[int]
    director: Optional[str]
    cast: Optional[str]
    synopsis: Optional[str]
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[MovieResponse])
async def list_movies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """全映画取得"""
    movies = db.query(Movie).offset(skip).limit(limit).all()
    return movies

@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int, db: Session = Depends(get_db)):
    """映画詳細取得"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="映画が見つかりません")
    return movie
