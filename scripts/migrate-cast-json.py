#!/usr/bin/env python3
"""
movies.cast を JSON文字列へ正規化する移行スクリプト
"""
from backend.app.db.database import SessionLocal
from backend.app.models.models import Movie
from backend.app.utils.cast_utils import dump_cast_text, parse_cast_text


def main():
    db = SessionLocal()
    try:
        movies = db.query(Movie).all()
        converted = 0
        for movie in movies:
            normalized = dump_cast_text(parse_cast_text(movie.cast))
            if movie.cast != normalized:
                movie.cast = normalized
                converted += 1

        db.commit()
        print(f"cast normalized: {converted} / {len(movies)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
