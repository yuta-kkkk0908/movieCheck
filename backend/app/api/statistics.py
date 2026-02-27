"""
統計・分析 API
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Movie, Record

router = APIRouter()


class StatisticsResponse(BaseModel):
    """統計情報レスポンス（統一仕様）"""

    total_movies: int
    total_records: int
    recent_90_days: int
    top_genre: Optional[str]
    average_rating: float
    genre_stats: List[Dict]
    mood_stats: List[Dict]
    viewing_method_stats: List[Dict]
    rating_distribution: List[Dict]
    recent_records: List[Dict]


def _compute_overview(db: Session) -> Dict:
    """統一統計レスポンスを生成する。"""
    total_movies = db.query(func.count(Movie.id)).scalar() or 0
    total_records = db.query(func.count(Record.id)).scalar() or 0
    avg_rating = db.query(func.avg(Record.rating)).scalar() or 0.0

    since = datetime.utcnow() - timedelta(days=90)
    recent_90_days = db.query(func.count(Record.id)).filter(Record.viewed_date >= since).scalar() or 0

    genre_stats = []
    genre_results = (
        db.query(
            Movie.genre,
            func.count(Record.id).label("count"),
            func.avg(Record.rating).label("avg_rating"),
        )
        .join(Record, Movie.id == Record.movie_id)
        .filter(Movie.genre.isnot(None))
        .group_by(Movie.genre)
        .all()
    )

    top_genre = None
    top_genre_count = -1
    for genre, count, avg_rating_genre in genre_results:
        if not genre or count <= 0:
            continue

        genre_stats.append(
            {
                "name": genre,
                "value": count,
                "average_rating": float(avg_rating_genre) if avg_rating_genre else 0.0,
            }
        )
        if count > top_genre_count:
            top_genre = genre
            top_genre_count = count

    mood_stats = []
    mood_results = (
        db.query(Record.mood, func.count(Record.id).label("count"))
        .filter(Record.mood.isnot(None))
        .group_by(Record.mood)
        .all()
    )
    for mood, count in mood_results:
        if mood:
            mood_stats.append({"name": mood.value if hasattr(mood, "value") else mood, "value": count})

    viewing_method_stats = []
    viewing_results = db.query(Record.viewing_method, func.count(Record.id).label("count")).group_by(Record.viewing_method).all()
    for method, count in viewing_results:
        if method:
            viewing_method_stats.append({"name": method.value if hasattr(method, "value") else method, "value": count})

    rating_distribution = []
    for i in range(5):
        rating_min = i + 1
        rating_max = i + 2
        count = (
            db.query(func.count(Record.id))
            .filter(Record.rating >= rating_min, Record.rating < rating_max)
            .scalar()
            or 0
        )
        rating_distribution.append({"range": f"{rating_min}-{rating_max}", "count": count})

    recent_records = []
    recent_data = (
        db.query(Record, Movie)
        .join(Movie, Record.movie_id == Movie.id)
        .order_by(Record.viewed_date.desc())
        .limit(10)
        .all()
    )
    for record, movie in recent_data:
        recent_records.append(
            {
                "id": record.id,
                "title": movie.title,
                "viewed_date": record.viewed_date.isoformat(),
                "rating": record.rating,
                "mood": record.mood.value if getattr(record, "mood", None) else None,
                "viewing_method": record.viewing_method.value if getattr(record, "viewing_method", None) else None,
            }
        )

    return {
        "total_movies": total_movies,
        "total_records": total_records,
        "recent_90_days": recent_90_days,
        "top_genre": top_genre,
        "average_rating": float(avg_rating),
        "genre_stats": genre_stats,
        "mood_stats": mood_stats,
        "viewing_method_stats": viewing_method_stats,
        "rating_distribution": rating_distribution,
        "recent_records": recent_records,
    }


@router.get("/overview", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """統一統計情報を取得（正規エンドポイント）。"""
    try:
        return _compute_overview(db)
    except Exception as e:
        print(f"統計取得エラー: {e}")
        return {
            "total_movies": 0,
            "total_records": 0,
            "recent_90_days": 0,
            "top_genre": None,
            "average_rating": 0.0,
            "genre_stats": [],
            "mood_stats": [],
            "viewing_method_stats": [],
            "rating_distribution": [],
            "recent_records": [],
        }


@router.get("/statistics/overview", response_model=StatisticsResponse)
async def get_statistics_legacy(response: Response, db: Session = Depends(get_db)):
    """
    互換エンドポイント（非推奨）。
    正規エンドポイント: /api/statistics/overview
    """
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Sun, 31 May 2026 23:59:59 GMT"
    response.headers["Link"] = '</api/statistics/overview>; rel="successor-version"'
    return await get_statistics(db)


@router.get("/timeline")
async def get_timeline(days: int = 30, db: Session = Depends(get_db)):
    """期間別の視聴数推移を取得。"""
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        timeline = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)

            count = (
                db.query(func.count(Record.id))
                .filter(Record.viewed_date >= date_start, Record.viewed_date < date_end)
                .scalar()
                or 0
            )

            timeline.append({"date": date.strftime("%Y-%m-%d"), "count": count})

        return timeline
    except Exception as e:
        print(f"タイムライン取得エラー: {e}")
        return []


@router.get("/mood-recommendations")
async def get_mood_recommendations(mood: str, db: Session = Depends(get_db)):
    """指定の気分で高評価の映画を取得（レコメンド）。"""
    try:
        recommendations = []
        results = (
            db.query(
                Movie,
                func.avg(Record.rating).label("avg_rating"),
                func.count(Record.id).label("view_count"),
            )
            .join(Record, Movie.id == Record.movie_id)
            .filter(Record.mood == mood, Record.rating.isnot(None))
            .group_by(Movie.id)
            .order_by(func.avg(Record.rating).desc())
            .limit(10)
            .all()
        )

        for movie, avg_rating, view_count in results:
            if avg_rating and avg_rating >= 3.5:
                recommendations.append(
                    {
                        "id": movie.id,
                        "title": movie.title,
                        "genre": movie.genre,
                        "average_rating": float(avg_rating),
                        "play_count": view_count,
                        "image_url": movie.image_url,
                    }
                )

        return recommendations
    except Exception as e:
        print(f"レコメンド取得エラー: {e}")
        return []
