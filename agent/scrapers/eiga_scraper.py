"""
映画.com スクレイパー - 改良版（ログイン対応強化）
"""
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Optional
from datetime import datetime
import time
import re
import urllib.parse

class MovieComScraper:
    """映画.com からの映画情報スクレイピング"""
    
    BASE_URL = "https://eiga.com"
    WATCHED_PAGE_URL = "https://eiga.com/user/watched/"
    LOGIN_URL = "https://eiga.com/login/"
    
    def __init__(self, headless: bool = False):
        """Seleniumドライバを初期化
        
        Args:
            headless: Trueの場合バックグラウンド実行、Falseの場合ブラウザウィンドウを表示
        """
        self.driver = None
        self.interactive = False
        self.user_id = None  # ログイン後に抽出されるユーザーID
        try:
            print("[DEBUG] ChromeOptions を作成中...")
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument('--headless')  # バックグラウンド実行
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            print("[DEBUG] Selenium Chrome ドライバを作成中...")
            # webdriver-manager を使わずに、Selenium が自動検出するように
            try:
                self.driver = webdriver.Chrome(options=options)
                if not headless:
                    self.driver.maximize_window()
                print("[DEBUG] Selenium ドライバを初期化しました")
            except Exception as e:
                print(f"[WARN] 通常のドライバ起動に失敗: {e}")
                print("[DEBUG] webdriver_manager を使用して試みます...")
                
                try:
                    driver_path = ChromeDriverManager().install()
                    print(f"[DEBUG] ChromeDriver パス: {driver_path}")
                    self.driver = webdriver.Chrome(
                        service=Service(driver_path),
                        options=options
                    )
                    if not headless:
                        self.driver.maximize_window()
                    print("[DEBUG] webdriver_manager でドライバを初期化しました")
                except Exception as e2:
                    print(f"[ERROR] webdriver_manager も失敗: {e2}")
                    import traceback
                    traceback.print_exc()
                    self.driver = None
        
        except Exception as e:
            print(f"[ERROR] 予期しないドライバ初期化エラー: {e}")
            import traceback
            traceback.print_exc()
            self.driver = None
    
    def login(self, email: str = None, password: str = None) -> bool:
        """
        映画.comにログイン
        
        Args:
            email: メールアドレス（Noneの場合は対話型：ユーザーが手動でログイン）
            password: パスワード（Noneの場合は対話型）
        
        Returns:
            ログイン成功したか
        """
        if not self.driver:
            print("[ERROR] ドライバが初期化されていません")
            return False
        
        try:
            print(f"[DEBUG] ログインページを取得: {self.LOGIN_URL}")
            self.driver.get(self.LOGIN_URL)
            time.sleep(3)
            
            # 対話型ログイン（メール・パスワードなし）
            if email is None or password is None:
                print("[DEBUG] 対話型ログインモードを開始")
                self.interactive = True
                print("ブラウザが開きます。ログインしてください（Facebook連携でも可）")
                print("ログイン完了後、このスクリプトが自動継続します。")
                
                # ログイン完了を検知: URL変化 → is_logged_in() 確認の優先度で
                initial_url = self.driver.current_url
                print(f"[DEBUG] 初期 URL: {initial_url}")

                # 最大 600 秒待機（2秒刻みで is_logged_in() を確認）
                max_wait = 600
                interval = 2
                waited = 0
                url_changed = False
                
                while waited < max_wait:
                    time.sleep(interval)
                    waited += interval
                    try:
                        current_url = self.driver.current_url
                    except Exception:
                        current_url = '<unknown>'
                    
                    # URL が初期URL から変わったか確認
                    if current_url != initial_url:
                        url_changed = True
                        print(f"[DEBUG] {waited}秒経過 - URL 変化を検出: {current_url}")
                    else:
                        print(f"[DEBUG] {waited}秒経過 - URL 未変: {current_url}")
                    
                    # URL が変わった後でのみ is_logged_in() を確認
                    if url_changed:
                        if self.is_logged_in():
                            # 念のため短時間待って状態が安定するか確認
                            time.sleep(1)
                            if self.is_logged_in():
                                print(f"[DEBUG] ログイン完了を検知（安定確認済）: {current_url}")
                                # ユーザーIDを現在のURLから抽出
                                self._extract_user_id(current_url)
                                
                                # ユーザーIDが抽出できたか確認し、マイページへ遷移
                                if self.user_id:
                                    self._navigate_to_user_movie_page()
                                
                                return True

                print("[WARN] ログイン待機がタイムアウト")
                return False
            
            # 自動ログイン（メール・パスワード入力）
            print(f"[DEBUG] 自動ログインを試行（メール: {email[:5]}***）")
            self.interactive = False
            
            # メール入力フィールドを待機
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            print("[DEBUG] メール入力フィールドが見つかりました")
            email_input.clear()
            email_input.send_keys(email)
            time.sleep(1)
            
            # パスワード入力
            password_input = self.driver.find_element(By.NAME, "password")
            print("[DEBUG] パスワード入力フィールドが見つかりました")
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(1)
            
            # ログインボタンをクリック
            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            print("[DEBUG] ログインボタンをクリック")
            login_button.click()
            
            # ログイン完了をポーリングで検証（最大 30 秒）
            max_wait = 30
            interval = 2
            waited = 0
            while waited < max_wait:
                time.sleep(interval)
                waited += interval
                print(f"[DEBUG] 自動ログイン後待機 {waited}s")
                if self.is_logged_in():
                    print("[DEBUG] 自動ログイン成功（ポーリング確認）")
                    # ユーザーIDを現在のURLから抽出
                    current_url = self.driver.current_url
                    self._extract_user_id(current_url)
                    
                    # ユーザーIDが抽出できたか確認し、マイページへ遷移
                    if self.user_id:
                        self._navigate_to_user_movie_page()
                    return True

            print("[WARN] 自動ログイン後もログイン状態を確認できませんでした（タイムアウト）")
            return False
        
        except Exception as e:
            print(f"[ERROR] ログインエラー: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def fetch_watched_movies(self) -> List[Dict]:
        """
        視聴済み映画の一覧を取得
        
        Returns:
            映画情報リスト
        """
        if not self.driver:
            print("[ERROR] ドライバが初期化されていません")
            return []
        
        try:
            print(f"[DEBUG] 視聴済みページを取得: {self.WATCHED_PAGE_URL}")

            # ユーザーIDが抽出されない場合、待機して抽出を試みる
            if not self.user_id:
                print("[DEBUG] ユーザーID が未取得です。ログイン完了を待機します...")
                if not self.is_logged_in():
                    print("[DEBUG] 現在ログインされていません。ログイン完了を待機します...")
                    # 長めに待つ（判定ベース）、ユーザがログイン操作を完了するまで待つ
                    max_wait = 600
                    interval = 2
                    waited = 0
                    while waited < max_wait:
                        time.sleep(interval)
                        waited += interval
                        print("[DEBUG] ログイン待機中: {waited}s")
                        if self.is_logged_in():
                            print("[DEBUG] ログインが確認されました。")
                            # ユーザーIDを抽出
                            self._extract_user_id(self.driver.current_url)
                            break
                    else:
                        print("[ERROR] ログインが確認できませんでした（タイムアウト）")
                        return []
                else:
                    # 既にログイン済みならユーザーID抽出
                    self._extract_user_id(self.driver.current_url)
            
            if not self.user_id:
                print("[ERROR] ユーザーID を抽出できませんでした")
                return []
            
            # マイページへ遷移（必要に応じて）
            self._navigate_to_user_movie_page()

            # ユーザーIDから視聴履歴ページのURLを構築
            watched_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
            print(f"[DEBUG] 視聴済みページを取得: {watched_url}")
            
            # 最初のページへアクセス
            self.driver.get(watched_url)
            time.sleep(2)
            
            # フィルターを「鑑賞済みのみ表示」に設定
            self._set_watched_filter()
            time.sleep(2)
            
            movies = []
            page_num = 1
            max_pages = 1000  # 無限ループ防止
            
            while page_num <= max_pages:
                print(f"[DEBUG] ページ {page_num} を取得中: {watched_url}?page={page_num}")
                # フィルター設定後のURLを使用
                if page_num > 1:
                    self.driver.get(f"{watched_url}?page={page_num}")
                    time.sleep(2)
                
                current_url = self.driver.current_url
                print(f"[DEBUG] 現在の URL: {current_url}")
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # list-my-data div を探す（新しいHTML構造）
                movie_divs = soup.find_all('div', class_='list-my-data')
                print(f"[DEBUG] ページ {page_num}: list-my-data = {len(movie_divs)} 件")
                
                if not movie_divs:
                    print("[WARN] このページに映画要素が見つかりません")
                    break
                
                for idx, div in enumerate(movie_divs):
                    try:
                        movie_data = self._parse_movie_div(div)
                        if movie_data:
                            movies.append(movie_data)
                            print(f"[DEBUG] 映画 {len(movies)}: {movie_data.get('title')} を追加")
                    except Exception as e:
                        print(f"[WARN] 映画パースエラー (div {idx}): {e}")
                        continue
                
                # 次ページへのリンクを確認
                next_link = soup.find('a', class_='next')
                if next_link:
                    print("[DEBUG] 次ページリンクを検出。次ページへ移動します...")
                    page_num += 1
                else:
                    print("[DEBUG] 次ページリンクが見つかりません。最後のページです")
                    break
            
            print(f"[DEBUG] 合計 {len(movies)} 件の映画を取得")
            return movies
        
        except Exception as e:
            print(f"[ERROR] 視聴済み映画取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_movie_div(self, div) -> Optional[Dict]:
        """
        list-my-data div から映画情報をパース
        
        Args:
            div: BeautifulSoupの div 要素（class="list-my-data"）
        
        Returns:
            映画情報辞書
        """
        try:
            # div の id から external_id を抽出（m{MOVIE_ID}）
            div_id = div.get('id', '')
            external_id = None
            match = re.search(r'm(\d+)', div_id)
            if match:
                external_id = match.group(1)
            
            if not external_id:
                print(f"[DEBUG] external_id が見つかりません。div_id={div_id}")
                return None
            
            # <h3 class="title"><a href="/movie/{ID}/">タイトル</a></h3> から正確にタイトルを抽出
            title_h3 = div.find('h3', class_='title')
            if not title_h3:
                print(f"[DEBUG] h3.title が見つかりません。external_id={external_id}")
                return None
            
            movie_link = title_h3.find('a')
            if not movie_link:
                print(f"[DEBUG] h3.title の中に <a> タグが見つかりません。external_id={external_id}")
                return None
            
            title = movie_link.get_text(strip=True)
            # タイトルが空または短すぎる場合はスキップ
            if not title or len(title.strip()) < 2:
                print(f"[DEBUG] タイトルが無効です。external_id={external_id}, title='{title}'")
                return None
            
            movie_url = movie_link.get('href', '')
            if movie_url and not movie_url.startswith('http'):
                movie_url = self.BASE_URL + movie_url
            
            print(f"[DEBUG] div id={div_id} -> external_id={external_id}, title='{title}', url={movie_url}")
            
            # 画像URL取得（divの最初のimg タグ）
            image_url = None
            img = div.find('img')
            if img and img.get('src'):
                image_url = img.get('src')
            
            # 公開日取得（small.time から）
            viewed_date = datetime.now()
            release_date = None
            time_elem = div.find('small', class_='time')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                # 「劇場公開日：2023年5月26日」のような形式から抽出
                try:
                    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', time_text)
                    if date_match:
                        year, month, day = date_match.groups()
                        release_date = datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
                except:
                    pass
            
            # レーティング取得（star_on.png の数）
            rating = None
            rating_span = div.find('span', class_='score-star')
            if rating_span:
                # star_on.pngの数を数える
                star_images = rating_span.find_all('img', src=re.compile(r'star_on\.png'))
                if star_images:
                    rating = len(star_images) * 1.0  # 1～5の評価
                    print(f"[DEBUG]   レート: {rating} 星")
            
            viewing_method = "other"
            
            return {
                'title': title,
                'viewed_date': viewed_date,
                'viewing_method': viewing_method,
                'rating': rating,
                'movie_url': movie_url,
                'external_id': external_id,
                'image_url': image_url,
                'release_date': release_date
            }
        
        except Exception as e:
            print(f"[WARN] パースエラー: {e}")
            return None

    def is_logged_in(self) -> bool:
        """ページ内容からログイン状態を判定するユーティリティ
        
        注意: OAuth認可画面での誤認防止のため、クッキー判定は使用しない。
        ページ上の「ログアウト」「マイページ」等の表記のみで判定する。

        戻り値:
            True: ログイン済みと判断
            False: ログインしていない、または判定できない
        """
        try:
            page = self.driver.page_source
            current_url = self.driver.current_url
            
            # OAuth認可画面（/authorize/ を含む）はログイン中と見なさない
            if 'authorize' in current_url.lower():
                print(f"[DEBUG] OAuth認可画面と判定: {current_url}")
                return False

            # ページ上の文言で判定（ログアウト、マイページ等）
            if re.search(r'ログアウト|マイページ|マイページへ', page):
                print("[DEBUG] ページ上にログアウトまたはマイページ表記を検出")
                return True

            # ログインフォームが存在しないならログイン済みの可能性
            soup = BeautifulSoup(page, 'html.parser')
            if not soup.find('input', attrs={'name': 'email'}) and not soup.find('input', attrs={'name': 'password'}):
                print("[DEBUG] ログインフォームが見当たらないためログイン済みと推定")
                return True

            print("[DEBUG] ログイン済みではないと判断")
            return False
        except Exception as e:
            print(f"[WARN] is_logged_in チェック中に例外: {e}")
            return False
    
    def _extract_user_id(self, url: str) -> None:
        """URLからユーザーIDを抽出して保存
        
        Args:
            url: 対象URL（例: https://eiga.com/user/267148/movie/）
        """
        try:
            # /user/{USER_ID}/ パターンから user_id を抽出
            match = re.search(r'/user/(\d+)/', url)
            if match:
                self.user_id = match.group(1)
                print(f"[DEBUG] ユーザーID を抽出しました: {self.user_id}")
            else:
                print(f"[DEBUG] ユーザーID パターンが見つかりません: {url}")
        except Exception as e:
            print(f"[WARN] ユーザーID 抽出エラー: {e}")
    
    def _navigate_to_user_movie_page(self) -> None:
        """
        ユーザーのマイページ（映画視聴履歴）へ遷移
        
        /authorize/done ページから自動的にマイページへ遷移します。
        ユーザーIDが設定されていない場合、リダイレクト後の URL から抽出します。
        """
        try:
            current_url = self.driver.current_url
            print(f"[DEBUG] _navigate_to_user_movie_page() 開始。現在URL: {current_url}")

            # 既に user ページにいるか確認
            if self.user_id and re.search(rf'/user/{self.user_id}/', current_url):
                print(f"[DEBUG] 既にユーザーマイページにいます: {current_url}")
                return

            # 汎用ヘルパ: ページ内のリンクから user_id を探して遷移
            def _find_and_navigate_user_link():
                try:
                    soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                    # a タグで /user/xxx/ を含むものを探す
                    a = soup.find('a', href=re.compile(r'/user/\d+(/|)'))
                    if a and a.get('href'):
                        href = a.get('href')
                        if not href.startswith('http'):
                            href = self.BASE_URL + href
                        print(f"[DEBUG] ページ内のユーザリンクを発見: {href}")
                        self.driver.get(href)
                        time.sleep(2)
                        return True
                except Exception as e:
                    print(f"[WARN] ページ内リンク探索失敗: {e}")
                return False

            # /authorize/done ページにいる場合、univLink 等をクリックしてリダイレクトを待つ
            if '/authorize/done' in current_url.lower():
                print("[DEBUG] /authorize/done ページを検出。univLink を試行します")
                clicked = False
                try:
                    # try class name
                    univ = self.driver.find_element(By.CLASS_NAME, 'univLink')
                    self.driver.execute_script("arguments[0].scrollIntoView();", univ)
                    time.sleep(0.3)
                    univ.click()
                    clicked = True
                    print("[DEBUG] univLink をクリックしました")
                except Exception:
                    try:
                        # try common xpath
                        link = self.driver.find_element(By.XPATH, "//a[contains(@href, '/login/oauth/gid/')]")
                        self.driver.execute_script("arguments[0].scrollIntoView();", link)
                        time.sleep(0.3)
                        link.click()
                        clicked = True
                        print("[DEBUG] XPath のログイン戻りリンクをクリックしました")
                    except Exception as e:
                        print(f"[WARN] ログイン戻りリンクが見つかりません: {e}")

                # クリックしたらリダイレクト先をポーリングして user_id を抽出
                if clicked:
                    timeout = 15
                    interval = 0.5
                    waited = 0
                    while waited < timeout:
                        time.sleep(interval)
                        waited += interval
                        try:
                            cur = self.driver.current_url
                        except Exception:
                            cur = ''
                        if re.search(r'/user/\d+/', cur):
                            print(f"[DEBUG] リダイレクトでユーザURL検出: {cur}")
                            self._extract_user_id(cur)
                            if self.user_id:
                                movie_page_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
                                print(f"[DEBUG] マイページへ遷移: {movie_page_url}")
                                self.driver.get(movie_page_url)
                                time.sleep(2)
                                return
                            break

                    # クリックしても user_id が取れない場合、ページ内リンクを探す
                    if not self.user_id:
                        found = _find_and_navigate_user_link()
                        if found:
                            cur2 = self.driver.current_url
                            self._extract_user_id(cur2)
                            if self.user_id:
                                movie_page_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
                                print(f"[DEBUG] ページ内リンク経由でマイページへ遷移: {movie_page_url}")
                                self.driver.get(movie_page_url)
                                time.sleep(2)
                                return

                # クリックが無効ならページ内リンクを試す
                else:
                    if _find_and_navigate_user_link():
                        cur3 = self.driver.current_url
                        self._extract_user_id(cur3)
                        if self.user_id:
                            movie_page_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
                            print(f"[DEBUG] ページ内リンク経由でマイページへ遷移: {movie_page_url}")
                            self.driver.get(movie_page_url)
                            time.sleep(2)
                            return

            # user_id が既にあれば直接遷移
            if self.user_id:
                movie_page_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
                print(f"[DEBUG] ユーザマイページへ直接遷移: {movie_page_url}")
                self.driver.get(movie_page_url)
                time.sleep(2)
                return

            print("[WARN] user_id を取得できなかったため、自動遷移をスキップします")

        except Exception as e:
            print(f"[WARN] マイページ遷移エラー: {e}")
            import traceback
            traceback.print_exc()
    
    def _set_watched_filter(self) -> None:
        """
        フィルター設定：「鑑賞済みのみ表示」を選択
        
        ページ内の <select name="filter"> で value="watched" を選択
        """
        try:
            print("[DEBUG] フィルター設定を試みています...")
            
            # select 要素を探す
            select_elem = self.driver.find_element(By.NAME, "filter")
            print("[DEBUG] filter select 要素が見つかりました")
            
            # "watched" オプションを選択
            option_elem = select_elem.find_element(By.CSS_SELECTOR, "option[value='watched']")
            
            # JavaScriptで値を設定（一部のSelectは click では動作しない場合がある）
            self.driver.execute_script("arguments[0].value = 'watched';", select_elem)
            print("[DEBUG] フィルター値を 'watched' に設定しました")
            
            # オプションをクリック
            option_elem.click()
            time.sleep(1)
            
            # フォーム送信（チェンジイベントをトリガー）
            self.driver.execute_script("""
                var selectElem = document.querySelector('select[name="filter"]');
                if (selectElem) {
                    selectElem.value = 'watched';
                    // change イベントを発火
                    var event = new Event('change', { bubbles: true });
                    selectElem.dispatchEvent(event);
                }
            """)
            print("[DEBUG] フィルター設定完了（change イベント発火）")
            time.sleep(2)  # ページ再読み込み待機
        
        except Exception as e:
            print(f"[WARN] フィルター設定エラー: {e}")
            # フィルター設定失敗時は処理を続行（全データで取得）
            pass
    
    def get_movie_details(self, movie_url: str) -> Optional[Dict]:
        """
        映画詳細情報取得
        
        Args:
            movie_url: 映画ページURL
        
        Returns:
            映画詳細情報
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(movie_url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトル
            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # 公開年・ジャンル
            year = None
            genre = None
            info_text = soup.find('p', class_='c-movie-info__text')
            if info_text:
                parts = info_text.get_text(strip=True).split('/')
                if len(parts) >= 1:
                    try:
                        year = int(parts[0].strip())
                    except:
                        pass
                if len(parts) >= 2:
                    genre = parts[1].strip()
            
            # あらすじ
            synopsis = None
            synopsis_elem = soup.find('p', class_='c-movie-synopsis')
            if synopsis_elem:
                synopsis = synopsis_elem.get_text(strip=True)
            
            # 監督
            director = None
            director_elems = soup.find_all('a', class_='c-staff-link')
            if director_elems:
                director = director_elems[0].get_text(strip=True)
            
            # キャスト取得
            cast = []
            cast_elems = soup.find_all('a', class_='c-cast-link')
            for elem in cast_elems[:5]:  # 最初の5人
                cast.append(elem.get_text(strip=True))
            
            # 画像
            image_url = None
            img_elem = soup.find('img', class_='c-movie-poster')
            if img_elem:
                image_url = img_elem.get('src')
            
            return {
                'title': title,
                'released_year': year,
                'genre': genre,
                'director': director,
                'cast': cast,
                'synopsis': synopsis,
                'image_url': image_url,
                'external_id': movie_url.split('/')[-2] if (movie_url and isinstance(movie_url, str) and '/' in movie_url) else None
            }
        
        except Exception as e:
            print(f"詳細取得エラー: {e}")
            return None
    
    
    def close(self):
        """ドライバをクローズ"""
        if self.driver:
            try:
                self.driver.quit()
                print("[DEBUG] ドライバを閉じました")
            except:
                pass
    
    def __del__(self):
        """デストラクタ"""
        self.close()

    
    def search(self, query: str, max_results: int = 30) -> List[Dict]:
        """
        映画を検索
        
        Args:
            query: 検索キーワード
            max_results: 最大結果数
        
        Returns:
            検索結果リスト
        """
        if not self.driver:
            return []
        
        results: List[Dict] = []
        try:
            q = urllib.parse.quote_plus(query)
            search_url = f"{self.BASE_URL}/search/?q={q}"
            print(f"[DEBUG] 検索 URL: {search_url}")
            self.driver.get(search_url)
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # 映画へのリンクを抽出
            anchors = soup.find_all('a', href=re.compile(r'/movie/\d+'))
            print(f"[DEBUG] 検索結果: {len(anchors)} 件")
            
            seen = set()
            for a in anchors:
                if len(results) >= max_results:
                    break
                
                href = a.get('href')
                if not href:
                    continue
                
                movie_url = urllib.parse.urljoin(self.BASE_URL, href)
                if movie_url in seen:
                    continue
                seen.add(movie_url)
                
                title = a.get_text(strip=True)
                if not title:
                    title = a.get('title', '')
                
                if not title:
                    continue
                
                # 画像
                img = None
                img_tag = a.find('img')
                if img_tag:
                    img = img_tag.get('src') or img_tag.get('data-src')
                
                # external_id を安全に抽出
                external_id = None
                if '/' in href:
                    parts = href.split('/')
                    for i, part in enumerate(parts):
                        if part == 'movie' and i + 1 < len(parts):
                            external_id = parts[i + 1]
                            break
                
                results.append({
                    'title': title,
                    'released_year': None,
                    'genre': None,
                    'image_url': img,
                    'movie_url': movie_url,
                    'external_id': external_id
                })
            
            print(f"[DEBUG] {len(results)} 件の検索結果を返却")
            return results
        
        except Exception as e:
            print(f"[ERROR] 検索エラー: {e}")
            import traceback
            traceback.print_exc()
            return []
