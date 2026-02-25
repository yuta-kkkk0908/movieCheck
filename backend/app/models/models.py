"""
データモデル定義
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.db.database import Base

class Movie(Base):
    """映画テーブル"""
    __tablename__ = "movies"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    genre = Column(String(255))
    released_year = Column(Integer)
    director = Column(String(255))
    cast = Column(Text)  # JSON形式で複数キャスト格納
    synopsis = Column(Text)
    image_url = Column(String(500))
    external_id = Column(String(255), unique=True)  # 映画.comのID等
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    records = relationship("Record", back_populates="movie")

class ViewingMethod(str, enum.Enum):
    """視聴方法"""
    THEATER = "theater"       # 映画館
    STREAMING = "streaming"   # ストリーミング
    TV = "tv"                # TV放送
    DVD = "dvd"              # DVD/Blu-ray
    OTHER = "other"          # その他

class Mood(str, enum.Enum):
    """気分"""
    HAPPY = "happy"           # 楽しい
    SAD = "sad"              # 悲しい
    EXCITED = "excited"      # 興奮
    RELAXED = "relaxed"      # リラックス
    THOUGHTFUL = "thoughtful"# 考察的
    SCARY = "scary"          # 怖い
    ROMANTIC = "romantic"    # ロマンティック

class Record(Base):
    """視聴記録テーブル"""
    __tablename__ = "records"
    
    id = Column(Integer, primary_key=True, index=True)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    viewed_date = Column(DateTime, nullable=False)
    viewing_method = Column(Enum(ViewingMethod), nullable=False)
    rating = Column(Float)  # 1.0 - 5.0
    mood = Column(Enum(Mood))
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    movie = relationship("Movie", back_populates="records")

class EigaComCredentials(Base):
    """映画.com ログイン情報"""
    __tablename__ = "eiga_credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True)
    password_encrypted = Column(Text, nullable=False)  # 暗号化済み
    is_active = Column(Boolean, default=True)
    last_sync = Column(DateTime, nullable=True)  # 最後の同期日時
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
