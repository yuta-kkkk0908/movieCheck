"""
タスク処理（映画情報取得・登録）
"""
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.models import Movie, Record, EigaComCredentials, ViewingMethod
from app.db.encryption import EncryptionManager
from agent.scrapers.eiga_scraper import MovieComScraper
from typing import Dict, Optional, List
from datetime import datetime
class MovieAgent:
    """映画情報取得エージェント"""

    @staticmethod
    def register_movie(movie_data: Dict, movie_url: str) -> Optional[Movie]:
        """
        映画を登録（スクレイピングして詳細情報を自動取得）

        Args:
            movie_data: 初期映画情報（タイトル等）
            movie_url: 映画.comのURL

        Returns:
            作成された映画オブジェクト
        """
        db = SessionLocal()
        try:
            # 既存チェック（外部IDまたはタイトル）
            existing = None
            external_id = movie_data.get('external_id')
            if external_id:
                existing = db.query(Movie).filter(Movie.external_id == external_id).first()

            if not existing:
                existing = db.query(Movie).filter(Movie.title == movie_data.get('title')).first()

            if existing:
                return existing

            scraper = MovieComScraper()
            try:
                details = scraper.get_movie_details(movie_url) if movie_url else None
            finally:
                scraper.close()

            if not details:
                details = movie_data

            movie = Movie(
                title=details.get('title', movie_data.get('title')),
                genre=details.get('genre'),
                released_year=(details.get('released_year') or (
                    details.get('release_date').year if details.get('release_date') else None
                )),
                director=details.get('director'),
                cast=str(details.get('cast', [])),
                synopsis=details.get('synopsis'),
                image_url=details.get('image_url'),
                external_id=details.get('external_id') or external_id
            )

            db.add(movie)
            db.commit()
            db.refresh(movie)
            return movie

        except Exception as e:
            print(f"登録エラー: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    @staticmethod
    def sync_from_eiga_com(email: str = None, password: str = None) -> Dict:
        """
        映画.comから視聴履歴を同期

        Args:
            email: メールアドレス（Noneの場合は対話型ログイン）
            password: パスワード（Noneの場合は対話型ログイン）

        Returns:
            同期結果（新規追加数、既存数等）
        """
        db = SessionLocal()
        scraper = None

        try:
            print(f"[SYNC] 同期を開始します。インタラクティブモード: {email is None and password is None}")
            
            # headless=Falseで対話型ブラウザを表示
            print("[SYNC] スクレイパーを初期化中...")
            scraper = MovieComScraper(headless=False)
            
            if not scraper.driver:
                print("[SYNC] [ERROR] スクレイパーのドライバが初期化されていません")
                return {
                    'success': False,
                    'message': 'スクレイパーの初期化に失敗しました',
                    'added': 0,
                    'existing': 0,
                    'errors': 1
                }
            
            print("[SYNC] スクレイパー初期化完了")

            print("[SYNC] ログインを試行中...")
            if not scraper.login(email, password):
                print("[SYNC] [ERROR] ログイン失敗")
                return {
                    'success': False,
                    'message': 'ログインに失敗しました',
                    'added': 0,
                    'existing': 0,
                    'errors': 0
                }

            print("[SYNC] ログイン成功。映画データを取得中...")
            movies_data = scraper.fetch_watched_movies()
            print(f"[SYNC] {len(movies_data)} 件の映画を取得しました")

            added_count = 0
            existing_count = 0
            error_count = 0

            for movie_data in movies_data:
                try:
                    # 外部IDまたはタイトルで既存チェック
                    external_id = movie_data.get('external_id')
                    movie = None
                    
                    if external_id:
                        movie = db.query(Movie).filter(Movie.external_id == external_id).first()
                    
                    if not movie:
                        movie = db.query(Movie).filter(Movie.title == movie_data['title']).first()

                    if not movie:
                        movie_url = movie_data.get('movie_url', '')
                        details = scraper.get_movie_details(movie_url) if movie_url else {}

                        if details:
                            movie = Movie(
                                title=details.get('title', movie_data['title']),
                                genre=details.get('genre'),
                                released_year=details.get('released_year'),
                                director=details.get('director'),
                                cast=str(details.get('cast', [])),
                                synopsis=details.get('synopsis'),
                                image_url=details.get('image_url'),
                                external_id=details.get('external_id') or external_id
                            )
                        else:
                            movie = Movie(
                                title=movie_data['title'],
                                external_id=external_id,
                                released_year=(movie_data.get('release_date').year if movie_data.get('release_date') else None),
                                image_url=movie_data.get('image_url')
                            )

                        try:
                            db.add(movie)
                            db.flush()
                            added_count += 1
                            print(f"[SYNC] ✓ 映画を追加しました: {movie_data['title']} (ID: {external_id})")
                        except Exception as e:
                            # UNIQUE 制約エラーなど、既に存在する場合
                            if 'UNIQUE' in str(e) or 'unique' in str(e).lower():
                                print(f"[SYNC] ⚠ 映画は既に存在します（制約エラー）: {movie_data['title']} (ID: {external_id})")
                                existing_count += 1
                                db.rollback()
                            else:
                                raise
                    else:
                        existing_count += 1
                        print(f"[SYNC] ⚠ 映画は既に存在します: {movie_data['title']} (ID: {external_id})")

                    # 既に取得済みか確認
                    if movie:
                        existing_record = db.query(Record).filter(
                            Record.movie_id == movie.id,
                            Record.viewed_date == movie_data['viewed_date']
                        ).first()

                        if not existing_record:
                            record = Record(
                                movie_id=movie.id,
                                viewed_date=movie_data['viewed_date'],
                                viewing_method=movie_data.get('viewing_method', 'other'),
                                rating=movie_data.get('rating'),
                                mood=None,
                                comment='自動同期'
                            )
                            db.add(record)
                            db.flush()
                            print(f"[SYNC] ✓ 視聴記録を追加しました: {movie_data['title']}")

                except Exception as e:
                    print(f"[SYNC] ✗ 映画処理エラー: {e}")
                    error_count += 1
                    db.rollback()

            cred = None
            # 自動ログイン（credentials 有り）の場合のみ保存
            if email and password:
                cred = db.query(EigaComCredentials).filter(EigaComCredentials.email == email).first()
                if not cred:
                    cred = EigaComCredentials(email=email, password_encrypted=EncryptionManager.encrypt(password))
                    db.add(cred)
                else:
                    cred.password_encrypted = EncryptionManager.encrypt(password)
                cred.last_sync = datetime.utcnow()

            db.commit()

            return {
                'success': True,
                'message': '同期完了',
                'added': added_count,
                'existing': existing_count,
                'errors': error_count
            }

        except Exception as e:
            print(f"同期エラー: {e}")
            db.rollback()
            return {
                'success': False,
                'message': f'同期中にエラーが発生しました: {str(e)}',
                'added': 0,
                'existing': 0,
                'errors': 1
            }

        finally:
            if scraper:
                scraper.close()
            db.close()

    @staticmethod
    def search_movies(query: str) -> list:
        """
        映画を検索

        Args:
            query: 検索キーワード

        Returns:
            検索結果リスト
        """
        scraper = MovieComScraper()
        try:
            return scraper.search(query)
        finally:
            scraper.close()
