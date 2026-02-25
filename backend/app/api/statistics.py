"""
統計API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Movie, Record
from datetime import datetime, timedelta

router = APIRouter()


@router.get('/statistics/overview')
async def overview(db: Session = Depends(get_db)):
    """基本統計を返す"""
    total_movies = db.query(Movie).count()
    total_records = db.query(Record).count()

    # 最近90日内の視聴数
    since = datetime.utcnow() - timedelta(days=90)
    recent_90 = db.query(Record).filter(Record.viewed_date >= since).count()

    # ジャンル上位（簡易）
    genres = db.query(Movie.genre).all()
    genre_counts = {}
    for g, in genres:
        if not g:
            continue
        for part in (g.split(',') if ',' in g else [g]):
            key = part.strip()
            if not key:
                continue
            genre_counts[key] = genre_counts.get(key, 0) + 1

    top_genre = None
    if genre_counts:
        top_genre = max(genre_counts.items(), key=lambda x: x[1])[0]

    return {
        'total_movies': total_movies,
        'total_records': total_records,
        'recent_90_days': recent_90,
        'top_genre': top_genre
    }
"""
統計・分析 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.db.database import get_db
from app.models.models import Movie, Record, Mood, ViewingMethod
from pydantic import BaseModel
from typing import List, Dict, Optional

router = APIRouter()

class StatisticsResponse(BaseModel):
    """統計情報レスポンス"""
    total_movies: int
    total_records: int
    average_rating: Optional[float]
    genre_stats: List[Dict]
    mood_stats: List[Dict]
    viewing_method_stats: List[Dict]
    rating_distribution: List[Dict]
    recent_records: List[Dict]

class GenreStats(BaseModel):
    genre: str
    count: int
    average_rating: Optional[float]

class MoodStats(BaseModel):
    mood: str
    count: int

@router.get("/overview")
async def get_statistics(db: Session = Depends(get_db)):
    """
    統計情報を取得
    """
    try:
        # 基本統計
        total_movies = db.query(func.count(Movie.id)).scalar() or 0
        total_records = db.query(func.count(Record.id)).scalar() or 0
        avg_rating = db.query(func.avg(Record.rating)).scalar() or 0.0
        
        # ジャンル別統計
        genre_stats = []
        genre_results = db.query(
            Movie.genre,
            func.count(Record.id).label('count'),
            func.avg(Record.rating).label('avg_rating')
        ).join(Record, Movie.id == Record.movie_id).filter(
            Movie.genre.isnot(None)
        ).group_by(Movie.genre).all()
        
        for genre, count, avg_rating_genre in genre_results:
            if genre and count > 0:
                genre_stats.append({
                    'name': genre,
                    'value': count,
                    'average_rating': float(avg_rating_genre) if avg_rating_genre else 0
                })
        
        # 気分別統計
        mood_stats = []
        mood_results = db.query(
            Record.mood,
            func.count(Record.id).label('count')
        ).filter(
            Record.mood.isnot(None)
        ).group_by(Record.mood).all()
        
        for mood, count in mood_results:
            if mood:
                mood_stats.append({
                    'name': mood,
                    'value': count
                })
        
        # 視聴方法別統計
        viewing_method_stats = []
        viewing_results = db.query(
            Record.viewing_method,
            func.count(Record.id).label('count')
        ).group_by(Record.viewing_method).all()
        
        for method, count in viewing_results:
            if method:
                viewing_method_stats.append({
                    'name': method,
                    'value': count
                })
        
        # 評価分布
        rating_distribution = []
        for i in range(5):
            rating_min = i + 1
            rating_max = i + 2
            count = db.query(func.count(Record.id)).filter(
                Record.rating >= rating_min,
                Record.rating < rating_max
            ).scalar() or 0
            rating_distribution.append({
                'range': f'{rating_min}-{rating_max}',
                'count': count
            })
        
        # 最近の記録（10件）
        recent_records = []
        recent_data = db.query(Record, Movie).join(
            Movie, Record.movie_id == Movie.id
        ).order_by(Record.viewed_date.desc()).limit(10).all()
        
        for record, movie in recent_data:
            recent_records.append({
                'id': record.id,
                'title': movie.title,
                'viewed_date': record.viewed_date.isoformat(),
                'rating': record.rating,
                'mood': record.mood,
                'viewing_method': record.viewing_method
            })
        
        return {
            'total_movies': total_movies,
            'total_records': total_records,
            'average_rating': float(avg_rating),
            'genre_stats': genre_stats,
            'mood_stats': mood_stats,
            'viewing_method_stats': viewing_method_stats,
            'rating_distribution': rating_distribution,
            'recent_records': recent_records
        }
    
    except Exception as e:
        print(f"統計取得エラー: {e}")
        return {
            'total_movies': 0,
            'total_records': 0,
            'average_rating': 0,
            'genre_stats': [],
            'mood_stats': [],
            'viewing_method_stats': [],
            'rating_distribution': [],
            'recent_records': []
        }

@router.get("/timeline")
async def get_timeline(days: int = 30, db: Session = Depends(get_db)):
    """
    期間別の視聴数推移を取得
    
    Args:
        days: 過去N日間
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # 日別の視聴数
        timeline = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            date_end = date_start + timedelta(days=1)
            
            count = db.query(func.count(Record.id)).filter(
                Record.viewed_date >= date_start,
                Record.viewed_date < date_end
            ).scalar() or 0
            
            timeline.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })
        
        return timeline
    
    except Exception as e:
        print(f"タイムライン取得エラー: {e}")
        return []

@router.get("/mood-recommendations")
async def get_mood_recommendations(mood: str, db: Session = Depends(get_db)):
    """
    指定の気分で高評価の映画を取得（レコメンド）
    
    Args:
        mood: 気分
    """
    try:
        recommendations = []
        results = db.query(
            Movie,
            func.avg(Record.rating).label('avg_rating'),
            func.count(Record.id).label('view_count')
        ).join(Record, Movie.id == Record.movie_id).filter(
            Record.mood == mood,
            Record.rating.isnot(None)
        ).group_by(Movie.id).order_by(
            func.avg(Record.rating).desc()
        ).limit(10).all()
        
        for movie, avg_rating, view_count in results:
            if avg_rating and avg_rating >= 3.5:
                recommendations.append({
                    'id': movie.id,
                    'title': movie.title,
                    'genre': movie.genre,
                    'average_rating': float(avg_rating),
                    'play_count': view_count,
                    'image_url': movie.image_url
                })
        
        return recommendations
    
    except Exception as e:
        print(f"レコメンド取得エラー: {e}")
        return []
