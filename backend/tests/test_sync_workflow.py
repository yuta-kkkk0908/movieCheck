from datetime import datetime
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# `scripts/test-backend.sh` は backend/ をカレントにして pytest を実行するため、
# プロジェクトルートを import パスへ明示追加する。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import agent.tasks.movie_agent as movie_agent_module

if "app.models.models" in sys.modules:
    from app.models.models import Base, Movie, Record
else:
    from backend.app.models.models import Base, Movie, Record


class FakeScraper:
    scenario = "success"

    def __init__(self, headless=False):
        self.driver = object()
        self.cancelled = False
        self.cancel_reason = None

    def login(self, email=None, password=None):
        return True

    def fetch_watched_movies(self):
        if self.scenario == "fetch_exception":
            raise RuntimeError("fetch failed")
        return [
            {
                "title": "Test Movie",
                "external_id": "9999",
                "viewed_date": datetime(2025, 1, 1, 12, 0, 0),
                "movie_url": "https://eiga.com/movie/9999/",
                "viewing_method": "other",
                "rating": 4.0,
                "release_date": datetime(2024, 5, 1),
                "released_year": 2024,
                "director": "Director A",
            }
        ]

    def get_movie_details(self, movie_url):
        if self.scenario == "details_exception":
            raise RuntimeError("details failed")
        return {
            "title": "Test Movie",
            "genre": "Drama",
            "released_year": 2024,
            "director": "Director A",
            "cast": ["Actor A", "Actor B"],
            "synopsis": "Synopsis",
            "image_url": None,
            "external_id": "9999",
        }

    def close(self):
        return None


@pytest.fixture()
def isolated_db(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    monkeypatch.setattr(movie_agent_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(movie_agent_module, "MovieComScraper", FakeScraper)

    return TestSessionLocal


def test_sync_duplicate_prevention(isolated_db):
    FakeScraper.scenario = "success"

    result1 = movie_agent_module.MovieAgent.sync_from_eiga_com_with_options(
        email="user@example.com",
        password="secret",
        save_credentials=False,
        use_saved_credentials=False,
    )
    result2 = movie_agent_module.MovieAgent.sync_from_eiga_com_with_options(
        email="user@example.com",
        password="secret",
        save_credentials=False,
        use_saved_credentials=False,
    )

    db = isolated_db()
    try:
        assert result1["success"] is True
        assert result2["success"] is True
        assert db.query(Movie).count() == 1
        assert db.query(Record).count() == 1
        movie = db.query(Movie).first()
        assert movie.release_date == datetime(2024, 5, 1)
        assert movie.released_year == 2024
        assert movie.director == "Director A"
    finally:
        db.close()


def test_sync_rollback_on_exception(isolated_db):
    FakeScraper.scenario = "fetch_exception"

    result = movie_agent_module.MovieAgent.sync_from_eiga_com_with_options(
        email="user@example.com",
        password="secret",
        save_credentials=False,
        use_saved_credentials=False,
    )

    db = isolated_db()
    try:
        assert result["success"] is False
        assert db.query(Movie).count() == 0
        assert db.query(Record).count() == 0
    finally:
        db.close()


def test_sync_rerun_safety_after_failure(isolated_db):
    FakeScraper.scenario = "fetch_exception"
    failed = movie_agent_module.MovieAgent.sync_from_eiga_com_with_options(
        email="user@example.com",
        password="secret",
        save_credentials=False,
        use_saved_credentials=False,
    )

    FakeScraper.scenario = "success"
    succeeded = movie_agent_module.MovieAgent.sync_from_eiga_com_with_options(
        email="user@example.com",
        password="secret",
        save_credentials=False,
        use_saved_credentials=False,
    )

    db = isolated_db()
    try:
        assert failed["success"] is False
        assert succeeded["success"] is True
        assert db.query(Movie).count() == 1
        assert db.query(Record).count() == 1
    finally:
        db.close()


def test_sync_updates_existing_movie_metadata(isolated_db):
    FakeScraper.scenario = "success"

    db = isolated_db()
    try:
        movie = Movie(
            title="Test Movie",
            external_id="9999",
            release_date=None,
            released_year=None,
            director=None,
        )
        db.add(movie)
        db.commit()
    finally:
        db.close()

    result = movie_agent_module.MovieAgent.sync_from_eiga_com_with_options(
        email="user@example.com",
        password="secret",
        save_credentials=False,
        use_saved_credentials=False,
    )

    db = isolated_db()
    try:
        updated = db.query(Movie).filter(Movie.external_id == "9999").first()
        assert result["success"] is True
        assert updated is not None
        assert updated.release_date == datetime(2024, 5, 1)
        assert updated.released_year == 2024
        assert updated.director == "Director A"
        assert db.query(Record).count() == 1
    finally:
        db.close()
