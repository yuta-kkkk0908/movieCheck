"""
映画管理 API
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Movie
from app.utils.cast_utils import dump_cast_text, is_cast_empty, parse_cast_text
from agent.scrapers.eiga_scraper import MovieComScraper

router = APIRouter()


class MovieResponse(BaseModel):
    id: int
    title: str
    genre: Optional[str]
    release_date: Optional[datetime]
    released_year: Optional[int]
    director: Optional[str]
    cast: List[str]
    synopsis: Optional[str]
    image_url: Optional[str] = None
    external_id: Optional[str] = None


class RefreshDetailsRequest(BaseModel):
    force_update: bool = False


def _to_movie_response(movie: Movie) -> MovieResponse:
    return MovieResponse(
        id=movie.id,
        title=movie.title,
        genre=movie.genre,
        release_date=movie.release_date,
        released_year=movie.released_year,
        director=movie.director,
        cast=parse_cast_text(movie.cast),
        synopsis=movie.synopsis,
        image_url=movie.image_url,
        external_id=movie.external_id,
    )


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _build_movie_url(movie: Movie) -> Optional[str]:
    if not movie.external_id:
        return None
    return f"https://eiga.com/movie/{movie.external_id}/"


@router.get("/", response_model=List[MovieResponse])
async def list_movies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """全映画取得"""
    movies = db.query(Movie).offset(skip).limit(limit).all()
    return [_to_movie_response(movie) for movie in movies]


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(movie_id: int, db: Session = Depends(get_db)):
    """映画詳細取得"""
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="映画が見つかりません")
    return _to_movie_response(movie)


@router.post("/{movie_id}/refresh-details")
async def refresh_movie_details(
    movie_id: int,
    payload: RefreshDetailsRequest,
    db: Session = Depends(get_db),
):
    """
    映画詳細情報を再取得して更新する。
    - force_update=False: 空値のみ更新
    - force_update=True: 強制上書き
    """
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(status_code=404, detail="映画が見つかりません")

    movie_url = _build_movie_url(movie)
    if not movie_url:
        raise HTTPException(status_code=422, detail="external_id がないため詳細再取得できません")

    scraper = MovieComScraper()
    try:
        details = scraper.get_movie_details(movie_url)
    finally:
        scraper.close()

    if not details:
        raise HTTPException(status_code=502, detail="詳細情報の取得に失敗しました")

    updated_fields = []
    force = payload.force_update

    def apply_if_allowed(field_name: str, new_value):
        current = getattr(movie, field_name)
        if force or _is_empty(current):
            setattr(movie, field_name, new_value)
            updated_fields.append(field_name)

    apply_if_allowed("released_year", details.get("released_year"))
    apply_if_allowed("release_date", details.get("release_date"))
    apply_if_allowed("director", details.get("director"))
    apply_if_allowed("synopsis", details.get("synopsis"))
    apply_if_allowed("genre", details.get("genre"))
    apply_if_allowed("image_url", details.get("image_url"))

    new_cast = details.get("cast", [])
    if force or is_cast_empty(movie.cast):
        movie.cast = dump_cast_text(new_cast)
        updated_fields.append("cast")

    db.commit()
    db.refresh(movie)

    return {
        "success": True,
        "movie": _to_movie_response(movie).dict(),
        "updated_fields": updated_fields,
        "force_update": force,
    }
