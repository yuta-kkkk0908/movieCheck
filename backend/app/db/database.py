"""
データベース設定
"""
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# DB保存先
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "instance", "movies.db")

# DBディレクトリ作成
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# SQLiteエンジン設定
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """DBセッション取得"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """テーブル作成"""
    Base.metadata.create_all(bind=engine)
    _apply_lightweight_migrations()


def _apply_lightweight_migrations():
    """
    既存SQLiteに対する軽量マイグレーション。
    Alembic未導入環境向けに、必要最小限のカラム追加を行う。
    """
    inspector = inspect(engine)
    if "movies" not in inspector.get_table_names():
        return

    movie_columns = {col["name"] for col in inspector.get_columns("movies")}
    with engine.begin() as conn:
        if "release_date" not in movie_columns:
            conn.execute(text("ALTER TABLE movies ADD COLUMN release_date DATETIME"))
