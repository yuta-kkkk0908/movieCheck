"""
タスク処理（映画情報取得・登録）
"""
try:
    # backend/ 配下から起動する通常実行系
    from app.db.database import SessionLocal
    from app.models.models import Movie, Record, EigaComCredentials
    from app.db.encryption import EncryptionManager
    from app.utils.cast_utils import dump_cast_text
except ModuleNotFoundError:
    # ルート実行（テスト等）向けフォールバック
    from backend.app.db.database import SessionLocal
    from backend.app.models.models import Movie, Record, EigaComCredentials
    from backend.app.db.encryption import EncryptionManager
    from backend.app.utils.cast_utils import dump_cast_text
from agent.scrapers.eiga_scraper import MovieComScraper
from typing import Dict, Optional
from datetime import datetime
import os
class MovieAgent:
    """映画情報取得エージェント"""

    @staticmethod
    def _parse_env_bool(value: Optional[str]) -> Optional[bool]:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return None

    @staticmethod
    def _extract_released_year(data: Optional[Dict]) -> Optional[int]:
        if not data:
            return None
        year = data.get("released_year")
        if isinstance(year, int):
            return year
        release_date = data.get("release_date")
        if release_date and hasattr(release_date, "year"):
            try:
                return int(release_date.year)
            except Exception:
                return None
        return None

    @staticmethod
    def _extract_release_date(data: Optional[Dict]) -> Optional[datetime]:
        if not data:
            return None
        release_date = data.get("release_date")
        if isinstance(release_date, datetime):
            return release_date
        return None

    @staticmethod
    def _update_movie_metadata(movie: Movie, movie_data: Dict, details: Optional[Dict] = None) -> bool:
        """既存映画の同期対象メタデータを更新する。"""
        updated = False

        candidate_release_date = (
            MovieAgent._extract_release_date(details)
            or MovieAgent._extract_release_date(movie_data)
        )
        if candidate_release_date and movie.release_date != candidate_release_date:
            movie.release_date = candidate_release_date
            updated = True

        candidate_year = (
            MovieAgent._extract_released_year(details)
            or MovieAgent._extract_released_year(movie_data)
        )
        if candidate_year and movie.released_year != candidate_year:
            movie.released_year = candidate_year
            updated = True

        candidate_director = None
        if details:
            candidate_director = details.get("director")
        if not candidate_director:
            candidate_director = movie_data.get("director")
        if candidate_director:
            candidate_director = str(candidate_director).strip()
        if candidate_director and movie.director != candidate_director:
            movie.director = candidate_director
            updated = True

        return updated

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
                release_date=(
                    MovieAgent._extract_release_date(details)
                    or MovieAgent._extract_release_date(movie_data)
                ),
                released_year=(details.get('released_year') or (
                    details.get('release_date').year if details.get('release_date') else None
                )),
                director=details.get('director'),
                cast=dump_cast_text(details.get('cast', [])),
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
        return MovieAgent.sync_from_eiga_com_with_options(
            email=email,
            password=password,
            save_credentials=False,
            use_saved_credentials=True
        )

    @staticmethod
    def _resolve_login_credentials(
        db,
        email: Optional[str],
        password: Optional[str],
        use_saved_credentials: bool
    ) -> Dict:
        # 1) 明示入力
        if email and password:
            return {
                "email": email,
                "password": password,
                "source": "explicit"
            }

        # 2) 保存済み有効資格情報
        if use_saved_credentials:
            cred = db.query(EigaComCredentials).filter(EigaComCredentials.is_active == True).order_by(
                EigaComCredentials.updated_at.desc()
            ).first()
            if cred:
                try:
                    decrypted = EncryptionManager.decrypt(cred.password_encrypted)
                except Exception:
                    return {
                        "error": "saved_credential_decrypt_failed",
                        "message": "保存済み資格情報の復号に失敗しました",
                        "can_fallback_to_interactive": True
                    }
                return {
                    "email": cred.email,
                    "password": decrypted,
                    "source": "saved"
                }

        # 3) 対話ログイン
        return {
            "email": None,
            "password": None,
            "source": "interactive"
        }

    @staticmethod
    def sync_from_eiga_com_with_options(
        email: Optional[str] = None,
        password: Optional[str] = None,
        save_credentials: bool = False,
        use_saved_credentials: bool = True
    ) -> Dict:
        db = SessionLocal()
        scraper = None
        cancelled_message = "ログインブラウザが閉じられたため、同期をキャンセルしました"

        try:
            resolved = MovieAgent._resolve_login_credentials(db, email, password, use_saved_credentials)
            if resolved.get("error"):
                return {
                    "success": False,
                    "cancelled": False,
                    "message": resolved["message"],
                    "added": 0,
                    "existing": 0,
                    "errors": 0,
                    "can_fallback_to_interactive": resolved.get("can_fallback_to_interactive", False)
                }

            login_email = resolved.get("email")
            login_password = resolved.get("password")
            auth_source = resolved.get("source")
            print(f"[SYNC] 同期を開始します。認証ソース: {auth_source}")
            
            # Windows 実行時は explicit/saved でも表示ブラウザを優先して、headless描画差分を回避
            forced_headless = MovieAgent._parse_env_bool(os.getenv("EIGA_SYNC_HEADLESS"))
            if forced_headless is not None:
                use_headless = forced_headless
                print(f"[SYNC] EIGA_SYNC_HEADLESS により起動モードを上書き: {use_headless}")
            else:
                use_headless = auth_source != "interactive"
                if os.name == "nt" and auth_source in ("explicit", "saved"):
                    use_headless = False
            print(f"[SYNC] ブラウザ起動モード: {'headless' if use_headless else 'headed'}")
            print("[SYNC] スクレイパーを初期化中...")
            scraper = MovieComScraper(headless=use_headless)
            
            if not scraper.driver:
                print("[SYNC] [ERROR] スクレイパーのドライバが初期化されていません")
                detail = f" ({scraper.init_error})" if getattr(scraper, "init_error", None) else ""
                hint = f" / {scraper.environment_hint}" if getattr(scraper, "environment_hint", None) else ""
                return {
                    'success': False,
                    'cancelled': False,
                    'message': f'スクレイパーの初期化に失敗しました{detail}{hint}',
                    'added': 0,
                    'existing': 0,
                    'errors': 1,
                    'can_fallback_to_interactive': True
                }
            
            print("[SYNC] スクレイパー初期化完了")

            print("[SYNC] ログインを試行中...")
            if not scraper.login(login_email, login_password):
                if scraper.cancelled:
                    print(f"[SYNC] [CANCELLED] {scraper.cancel_reason}")
                    db.rollback()
                    return {
                        'success': False,
                        'cancelled': True,
                        'message': cancelled_message,
                        'added': 0,
                        'existing': 0,
                        'errors': 0,
                        'can_fallback_to_interactive': False
                    }
                print("[SYNC] [ERROR] ログイン失敗")
                can_fallback = auth_source == "saved"
                return {
                    'success': False,
                    'cancelled': False,
                    'message': '保存済み資格情報でのログインに失敗しました' if can_fallback else 'ログインに失敗しました',
                    'added': 0,
                    'existing': 0,
                    'errors': 0,
                    'can_fallback_to_interactive': can_fallback
                }

            print("[SYNC] ログイン成功。映画データを取得中...")
            movies_data = scraper.fetch_watched_movies()
            if scraper.cancelled:
                print(f"[SYNC] [CANCELLED] {scraper.cancel_reason}")
                db.rollback()
                return {
                    'success': False,
                    'cancelled': True,
                    'message': cancelled_message,
                    'added': 0,
                    'existing': 0,
                    'errors': 0,
                    'can_fallback_to_interactive': False
                }
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
                        fallback_released_year = (
                            movie_data.get('released_year')
                            or (movie_data.get('release_date').year if movie_data.get('release_date') else None)
                        )
                        fallback_release_date = MovieAgent._extract_release_date(movie_data)
                        fallback_director = movie_data.get('director')

                        if details:
                            movie = Movie(
                                title=details.get('title', movie_data['title']),
                                genre=details.get('genre'),
                                release_date=MovieAgent._extract_release_date(details) or fallback_release_date,
                                released_year=details.get('released_year') or fallback_released_year,
                                director=details.get('director') or fallback_director,
                                cast=dump_cast_text(details.get('cast', [])),
                                synopsis=details.get('synopsis'),
                                image_url=details.get('image_url'),
                                external_id=details.get('external_id') or external_id
                            )
                        else:
                            movie = Movie(
                                title=movie_data['title'],
                                external_id=external_id,
                                release_date=fallback_release_date,
                                released_year=fallback_released_year,
                                director=fallback_director,
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
                        if MovieAgent._update_movie_metadata(movie, movie_data):
                            print(f"[SYNC] ↻ 映画メタ情報を更新しました: {movie_data['title']}")
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

            # 明示入力 + 保存ON の場合のみ保存
            if save_credentials and email and password:
                cred = db.query(EigaComCredentials).filter(EigaComCredentials.email == email).first()
                if not cred:
                    cred = EigaComCredentials(email=email, password_encrypted=EncryptionManager.encrypt(password))
                    db.add(cred)
                else:
                    cred.password_encrypted = EncryptionManager.encrypt(password)
                # 単一アクティブ運用
                db.query(EigaComCredentials).filter(EigaComCredentials.email != email).update(
                    {EigaComCredentials.is_active: False},
                    synchronize_session=False
                )
                cred.is_active = True
                cred.last_sync = datetime.utcnow()
            elif auth_source == "saved" and login_email:
                cred = db.query(EigaComCredentials).filter(EigaComCredentials.email == login_email).first()
                if cred:
                    cred.last_sync = datetime.utcnow()

            db.commit()

            return {
                'success': True,
                'cancelled': False,
                'message': '同期完了',
                'added': added_count,
                'existing': existing_count,
                'errors': error_count,
                'can_fallback_to_interactive': False
            }

        except Exception as e:
            if scraper and scraper.cancelled:
                print(f"[SYNC] [CANCELLED] {scraper.cancel_reason}")
                db.rollback()
                return {
                    'success': False,
                    'cancelled': True,
                    'message': cancelled_message,
                    'added': 0,
                    'existing': 0,
                    'errors': 0,
                    'can_fallback_to_interactive': False
                }
            print(f"同期エラー: {e}")
            db.rollback()
            return {
                'success': False,
                'cancelled': False,
                'message': f'同期中にエラーが発生しました: {str(e)}',
                'added': 0,
                'existing': 0,
                'errors': 1,
                'can_fallback_to_interactive': False
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
