"""
映画.com スクレイパー - 改良版（ログイン対応強化）
"""
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import (
    NoSuchWindowException,
    InvalidSessionIdException,
    NoAlertPresentException,
)
from webdriver_manager.chrome import ChromeDriverManager
from typing import List, Dict, Optional
from datetime import datetime
import time
import re
import urllib.parse
import os
import shutil
from collections import Counter
import html

class MovieComScraper:
    """映画.com からの映画情報スクレイピング"""
    
    BASE_URL = "https://eiga.com"
    WATCHED_PAGE_URL = "https://eiga.com/user/watched/"
    LOGIN_URL = "https://eiga.com/login/"
    AUTH_LOGIN_URL = (
        "https://id.eiga.com/authorize/"
        "?cid=eigacom_login&client_id=eigacom&gid_mode=login"
        "&redirect_uri=https%3A%2F%2Feiga.com%2Flogin%2Foauth%2Fgid%2F"
        "&response_type=code&scope=email%20profile"
    )
    OAUTH_ENTRY_URL = "https://eiga.com/login/oauth/gid/"

    @staticmethod
    def _is_wsl() -> bool:
        try:
            with open("/proc/version", "r", encoding="utf-8") as f:
                return "microsoft" in f.read().lower()
        except Exception:
            return False
    
    def __init__(self, headless: bool = False):
        """Seleniumドライバを初期化
        
        Args:
            headless: Trueの場合バックグラウンド実行、Falseの場合ブラウザウィンドウを表示
        """
        self.driver = None
        self.interactive = False
        self.user_id = None  # ログイン後に抽出されるユーザーID
        self.user_id_confirmed = False
        self.oauth_state = None
        self.cancelled = False
        self.cancel_reason = None
        self.init_error = None
        self.environment_hint = None
        try:
            print("[DEBUG] ChromeOptions を作成中...")
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument('--headless=new')  # バックグラウンド実行
            else:
                options.add_argument('--start-maximized')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--remote-allow-origins=*')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            chrome_binary = os.getenv("CHROME_BINARY_PATH")
            if not chrome_binary:
                chrome_binary = (
                    shutil.which("google-chrome")
                    or shutil.which("google-chrome-stable")
                    or shutil.which("chromium")
                    or shutil.which("chromium-browser")
                )
            if chrome_binary:
                options.binary_location = chrome_binary
                print(f"[DEBUG] CHROME_BINARY_PATH を使用: {chrome_binary}")

            init_errors = []

            def _finalize_window(driver_obj):
                if not headless:
                    try:
                        driver_obj.maximize_window()
                    except Exception as window_error:
                        print(f"[WARN] ウィンドウ最大化に失敗（起動は継続）: {window_error}")

            print("[DEBUG] Selenium Chrome ドライバを作成中...")
            try:
                self.driver = webdriver.Chrome(options=options)
                try:
                    self.driver.execute_cdp_cmd(
                        "Page.addScriptToEvaluateOnNewDocument",
                        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
                    )
                except Exception:
                    pass
                _finalize_window(self.driver)
                print("[DEBUG] Selenium Manager で Chrome ドライバを初期化しました")
            except Exception as e:
                init_errors.append(f"chrome_selenium_manager={e}")
                print(f"[WARN] Selenium Manager 経由の Chrome 起動に失敗: {e}")

            if not self.driver:
                chromedriver_path = os.getenv("CHROMEDRIVER_PATH")
                if not chromedriver_path:
                    chromedriver_path = shutil.which("chromedriver")
                if chromedriver_path:
                    print(f"[DEBUG] CHROMEDRIVER_PATH を使用して試行: {chromedriver_path}")
                    try:
                        self.driver = webdriver.Chrome(
                            service=Service(chromedriver_path),
                            options=options
                        )
                        try:
                            self.driver.execute_cdp_cmd(
                                "Page.addScriptToEvaluateOnNewDocument",
                                {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
                            )
                        except Exception:
                            pass
                        _finalize_window(self.driver)
                        print("[DEBUG] CHROMEDRIVER_PATH で Chrome ドライバを初期化しました")
                    except Exception as e:
                        init_errors.append(f"chrome_env_driver={e}")
                        print(f"[WARN] CHROMEDRIVER_PATH での起動に失敗: {e}")

            if not self.driver:
                print("[DEBUG] webdriver_manager を使用して試行...")
                try:
                    driver_path = ChromeDriverManager().install()
                    print(f"[DEBUG] ChromeDriver パス: {driver_path}")
                    self.driver = webdriver.Chrome(
                        service=Service(driver_path),
                        options=options
                    )
                    try:
                        self.driver.execute_cdp_cmd(
                            "Page.addScriptToEvaluateOnNewDocument",
                            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
                        )
                    except Exception:
                        pass
                    _finalize_window(self.driver)
                    print("[DEBUG] webdriver_manager で Chrome ドライバを初期化しました")
                except Exception as e:
                    init_errors.append(f"chrome_webdriver_manager={e}")
                    print(f"[WARN] webdriver_manager 経由の Chrome 起動に失敗: {e}")

            if not self.driver:
                print("[DEBUG] Edge ドライバをフォールバック試行...")
                try:
                    edge_options = webdriver.EdgeOptions()
                    if headless:
                        edge_options.add_argument("--headless")
                    edge_options.add_argument("--start-maximized")
                    self.driver = webdriver.Edge(options=edge_options)
                    _finalize_window(self.driver)
                    print("[DEBUG] Selenium Manager で Edge ドライバを初期化しました")
                except Exception as e:
                    init_errors.append(f"edge_selenium_manager={e}")
                    print(f"[WARN] Edge フォールバック起動に失敗: {e}")

            if not self.driver:
                self.init_error = " | ".join(init_errors)
                if self._is_wsl():
                    self.environment_hint = (
                        "WSL 上で実行中です。`google-chrome/chromium` と `chromedriver` が必要です。"
                        "例: sudo apt update && sudo apt install -y chromium chromium-driver。"
                        "または Windows 側でバックエンドを起動してください。"
                    )
                print(f"[ERROR] ドライバ初期化に失敗: {self.init_error}")
        
        except Exception as e:
            print(f"[ERROR] 予期しないドライバ初期化エラー: {e}")
            import traceback
            traceback.print_exc()
            self.init_error = str(e)
            self.driver = None

    def _is_browser_closed_error(self, error: Exception) -> bool:
        if isinstance(error, (NoSuchWindowException, InvalidSessionIdException)):
            return True
        text = str(error).lower()
        return (
            "no such window" in text
            or "target window already closed" in text
            or "invalid session id" in text
            or "disconnected: not connected to devtools" in text
            or "web view not found" in text
        )

    def _is_logged_out_ui(self) -> bool:
        """ヘッダーUIから未ログイン状態を判定する。"""
        try:
            page = self.driver.page_source
            current_url = self.driver.current_url.lower()
            if '/login/' in current_url and 'oauth/gid' not in current_url:
                return True
            if re.search(r'class="[^"]*head-account[^"]*log-out[^"]*"', page):
                if re.search(r'>\s*ログイン\s*<', page):
                    return True
            return False
        except Exception:
            return False

    def _mark_cancelled(self, reason: str) -> None:
        if not self.cancelled:
            self.cancelled = True
            self.cancel_reason = reason
            print(f"[INFO] 同期をキャンセル状態に設定: {reason}")

    def _accept_alert_if_present(self) -> bool:
        try:
            alert = self.driver.switch_to.alert
            text = alert.text
            print(f"[WARN] アラートを検出して受理します: {text}")
            alert.accept()
            return True
        except NoAlertPresentException:
            return False
        except Exception:
            return False

    def _ensure_active_window(self) -> bool:
        """現在ウィンドウが閉じられていた場合に生存ウィンドウへ切替える。"""
        if not self.driver:
            return False
        try:
            _ = self.driver.current_window_handle
            return True
        except Exception:
            try:
                handles = self.driver.window_handles
                if not handles:
                    return False
                self.driver.switch_to.window(handles[-1])
                _ = self.driver.current_window_handle
                print("[DEBUG] 生存ウィンドウへ切り替えました")
                return True
            except Exception:
                return False

    def is_driver_alive(self) -> bool:
        if not self.driver:
            return False
        if self._accept_alert_if_present():
            # アラート受理後にウィンドウ状態を再確認
            pass
        try:
            _ = self.driver.current_window_handle
            return True
        except Exception as e:
            if self._ensure_active_window():
                return True
            if self._is_browser_closed_error(e):
                self._mark_cancelled("ログインブラウザが閉じられたか、セッションが切断されました")
                return False
            return False

    def _find_element_across_frames(self, selectors, timeout: int = 10):
        """複数セレクタをトップ文書 + iframe 横断で探索して最初の要素を返す。"""
        if not self.driver:
            return None

        deadline = time.time() + timeout
        while time.time() < deadline:
            # 1) トップ文書
            try:
                self.driver.switch_to.default_content()
                for by, value in selectors:
                    elems = self.driver.find_elements(by, value)
                    if elems:
                        return elems[0]
            except Exception:
                pass

            # 2) iframe 内
            try:
                self.driver.switch_to.default_content()
                frames = self.driver.find_elements(By.TAG_NAME, "iframe")
                for idx in range(len(frames)):
                    try:
                        self.driver.switch_to.default_content()
                        frames = self.driver.find_elements(By.TAG_NAME, "iframe")
                        if idx >= len(frames):
                            break
                        self.driver.switch_to.frame(frames[idx])
                        for by, value in selectors:
                            elems = self.driver.find_elements(by, value)
                            if elems:
                                return elems[0]
                    except Exception:
                        continue
            except Exception:
                pass

            time.sleep(0.5)

        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass
        return None

    def _find_element_across_windows_and_frames(self, selectors, timeout: int = 10):
        """全ウィンドウ + iframe を横断して最初の一致要素を返す。"""
        if not self.driver:
            return None
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                handles = self.driver.window_handles
            except Exception:
                handles = []
            if not handles:
                handles = [self.driver.current_window_handle]

            for handle in handles:
                try:
                    self.driver.switch_to.window(handle)
                    elem = self._find_element_across_frames(selectors, timeout=1)
                    if elem:
                        return elem
                except Exception:
                    continue
            time.sleep(0.5)
        return None

    def _collect_oauth_callback_urls(self) -> List[str]:
        """DOM構造に依存せず、OAuth コールバックURL候補を収集する。"""
        candidates: List[str] = []
        try:
            page = self.driver.page_source or ""
            soup = BeautifulSoup(page, "html.parser")

            # 1) href/action/src 属性から収集
            for tag in soup.find_all(href=True):
                href = tag.get("href") or ""
                if "/login/oauth/gid/" in href:
                    candidates.append(self._normalize_oauth_callback_url(href))
            for tag in soup.find_all(action=True):
                action = tag.get("action") or ""
                if "/login/oauth/gid/" in action:
                    candidates.append(self._normalize_oauth_callback_url(action))

            # 2) 生HTML中のURL文字列から収集（DOM変更時フォールバック）
            decoded = html.unescape(page)
            regex_hits = re.findall(
                r'(https?://eiga\.com/login/oauth/gid/\?[^\s"\'<>]+|/login/oauth/gid/\?[^\s"\'<>]+)',
                decoded
            )
            for hit in regex_hits:
                candidates.append(self._normalize_oauth_callback_url(hit))
        except Exception as e:
            print(f"[WARN] OAuthコールバックURL収集中に例外: {e}")

        # 重複除去（順序維持）
        seen = set()
        deduped = [u for u in candidates if u and not (u in seen or seen.add(u))]

        # code+state を最優先、次に code のみ
        with_code_and_state = [
            u for u in deduped
            if re.search(r'[?&]code=[^&]+', u) and re.search(r'[?&]state=[^&]+', u)
        ]
        if with_code_and_state:
            return with_code_and_state
        with_code = [u for u in deduped if re.search(r'[?&]code=[^&]+', u)]
        if with_code:
            return with_code
        return [self.BASE_URL + "/login/oauth/gid/"]

    def _normalize_oauth_callback_url(self, url: str) -> str:
        if not url:
            return ""
        normalized = html.unescape(url).strip().strip('"').strip("'")
        if normalized.startswith("//"):
            normalized = "https:" + normalized
        elif normalized.startswith("/"):
            normalized = urllib.parse.urljoin(self.BASE_URL, normalized)
        elif normalized.startswith("eiga.com/"):
            normalized = "https://" + normalized
        return normalized

    @staticmethod
    def _has_oauth_state(url: str) -> bool:
        return bool(re.search(r'[?&]state=[^&]+', url or ""))

    def _fill_missing_oauth_state(self, url: str) -> str:
        """code はあるが state が無いURLに、保持済みstateを補完する。"""
        url = self._normalize_oauth_callback_url(url)
        if not url:
            return url
        if not re.search(r'[?&]code=[^&]+', url):
            return url
        if self._has_oauth_state(url):
            return url
        if self.oauth_state:
            sep = "&" if "?" in url else "?"
            filled = f"{url}{sep}state={urllib.parse.quote_plus(self.oauth_state)}"
            print(f"[DEBUG] state欠落URLへstateを補完: {filled}")
            return filled
        print(f"[DEBUG] state欠落URLをそのまま使用: {url}")
        return url

    def _get_authorize_done_callback_url(self) -> str:
        """authorize/done 画面の「映画.comへ戻る」URLを取得する。"""
        try:
            data = self.driver.execute_script(
                """
                const link = document.querySelector('div.row.link_btn a.univLink')
                    || document.querySelector("a.univLink[href*='/login/oauth/gid/']")
                    || Array.from(document.querySelectorAll("a[href*='/login/oauth/gid/']")).find(
                        (el) => (el.textContent || '').includes('映画.comへ戻る')
                    );
                if (!link) return null;
                return {
                    rawHref: link.getAttribute('href') || '',
                    absHref: link.href || ''
                };
                """
            )
            if not data:
                candidates = self._collect_oauth_callback_urls()
                for candidate in candidates:
                    normalized = self._normalize_oauth_callback_url(candidate)
                    if re.search(r"[?&]code=[^&]+", normalized):
                        return self._fill_missing_oauth_state(normalized)
                return ""
            href = (data.get("rawHref") or data.get("absHref") or "").strip()
            normalized = self._fill_missing_oauth_state(href)
            if re.search(r"[?&]code=[^&]+", normalized):
                return normalized
            candidates = self._collect_oauth_callback_urls()
            for candidate in candidates:
                fallback = self._normalize_oauth_callback_url(candidate)
                if re.search(r"[?&]code=[^&]+", fallback):
                    return self._fill_missing_oauth_state(fallback)
            return ""
        except Exception:
            return ""

    def _capture_state_from_dom(self):
        """現在ページのDOMから state を拾って保持する。"""
        try:
            # URL / referrer から先に回収
            try:
                cur = self.driver.current_url or ""
                m = re.search(r"[?&]state=([^&]+)", cur)
                if m:
                    self.oauth_state = urllib.parse.unquote_plus(m.group(1))
                    print(f"[DEBUG] current_url からstateを取得: {self.oauth_state}")
                    return
            except Exception:
                pass
            try:
                ref = self.driver.execute_script("return document.referrer || '';") or ""
                m = re.search(r"[?&]state=([^&]+)", ref)
                if m:
                    self.oauth_state = urllib.parse.unquote_plus(m.group(1))
                    print(f"[DEBUG] referrer からstateを取得: {self.oauth_state}")
                    return
            except Exception:
                pass

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            # hidden input
            inp = soup.find("input", attrs={"name": "state"})
            if inp and inp.get("value"):
                self.oauth_state = inp.get("value")
                print(f"[DEBUG] DOMからstateを取得: {self.oauth_state}")
                return
            # link href
            for a in soup.find_all("a", href=True):
                href = self._normalize_oauth_callback_url(a.get("href") or "")
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                state_val = qs.get("state", [None])[0]
                if state_val:
                    self.oauth_state = state_val
                    print(f"[DEBUG] link hrefからstateを取得: {self.oauth_state}")
                    return
        except Exception:
            pass

    def _debug_dump_login_oauth_candidates(self) -> None:
        """ログインページ上のOAuth関連リンク候補をデバッグ出力する。"""
        try:
            anchors = self.driver.find_elements(By.XPATH, "//a[@href]")
            samples = []
            for a in anchors:
                href = (a.get_attribute("href") or "").strip()
                text = (a.text or "").strip()
                if (
                    "/login/oauth/gid" in href
                    or "id.eiga.com" in href
                    or "/authorize/" in href
                    or "映画.com ID" in text
                ):
                    samples.append((href, text))
                if len(samples) >= 12:
                    break
            if samples:
                print("[DEBUG] ログインページOAuth候補リンク:")
                for idx, (href, text) in enumerate(samples, start=1):
                    print(f"[DEBUG]   {idx}. href={href} text={text}")
            else:
                print("[DEBUG] ログインページでOAuth候補リンクを検出できませんでした")
        except Exception as e:
            print(f"[WARN] OAuth候補リンクのダンプに失敗: {e}")

    def _open_authorize_via_login_page(self) -> bool:
        """映画.comログインページ上の正規導線から認可画面へ遷移する。"""
        try:
            deadline = time.time() + 8.0
            while time.time() < deadline:
                links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/login/oauth/gid')]"
                    "|//a[contains(@href, 'id.eiga.com/authorize')]"
                    "|//a[contains(@href, '/authorize/?cid=eigacom_login')]"
                )

                filtered = []
                for a in links:
                    href = (a.get_attribute("href") or "").strip()
                    text = (a.text or "").strip()
                    if "/info/lp" in href:
                        continue
                    filtered.append((a, href, text))

                if filtered:
                    priority = []
                    for a, href, text in filtered:
                        score = 0
                        if "/login/oauth/gid" in href:
                            score += 100
                        if "id.eiga.com/authorize" in href:
                            score += 80
                        if re.search(r"[?&]state=[^&]+", href):
                            score += 30
                        if "映画.com ID" in text:
                            score += 20
                        priority.append((score, a, href))
                    priority.sort(key=lambda x: x[0], reverse=True)
                    score, target, href = priority[0]
                    if score > 0:
                        print(f"[DEBUG] ログインページ導線から認可画面へ遷移: {href}")
                        try:
                            parsed = urllib.parse.urlparse(href)
                            qs = urllib.parse.parse_qs(parsed.query)
                            state_val = qs.get("state", [None])[0]
                            if state_val:
                                self.oauth_state = state_val
                                print(f"[DEBUG] 認可リンクからstateを取得: {self.oauth_state}")
                        except Exception:
                            pass
                        try:
                            target.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", target)
                        time.sleep(1.5)
                        try:
                            cur = self.driver.current_url
                            print(f"[DEBUG] 導線クリック後URL: {cur}")
                        except Exception:
                            pass
                        self._capture_state_from_dom()
                        return True

                text_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(normalize-space(.), '映画.com ID')]"
                    "|//button[contains(normalize-space(.), '映画.com ID')]"
                )
                if text_buttons:
                    target = text_buttons[0]
                    print("[DEBUG] テキスト導線（映画.com ID）をクリックします")
                    try:
                        target.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", target)
                    time.sleep(1.5)
                    try:
                        cur = self.driver.current_url
                        print(f"[DEBUG] テキスト導線クリック後URL: {cur}")
                    except Exception:
                        pass
                    self._capture_state_from_dom()
                    return True

                time.sleep(0.5)

            self._debug_dump_login_oauth_candidates()
            return False
        except Exception as e:
            print(f"[WARN] ログインページ導線での認可遷移に失敗: {e}")
            return False

    def _open_oauth_entry_direct(self) -> bool:
        """映画.com の OAuth エントリURLから正規フローを開始する。"""
        try:
            print(f"[DEBUG] OAuthエントリURLへ遷移: {self.OAUTH_ENTRY_URL}")
            self.driver.switch_to.default_content()
            self.driver.get(self.OAUTH_ENTRY_URL)
            time.sleep(1.5)
            try:
                cur = self.driver.current_url
            except Exception:
                cur = ""
            print(f"[DEBUG] OAuthエントリ遷移後URL: {cur}")
            m = re.search(r"[?&]state=([^&]+)", cur or "")
            if m:
                self.oauth_state = urllib.parse.unquote_plus(m.group(1))
                print(f"[DEBUG] OAuthエントリ遷移後URLからstateを取得: {self.oauth_state}")
            return True
        except Exception as e:
            print(f"[WARN] OAuthエントリURL遷移に失敗: {e}")
            return False

    def _extract_authorize_url_from_login_page(self) -> str:
        """ログインページHTMLから id.eiga.com の認可URLを抽出する。"""
        try:
            page = self.driver.page_source or ""
            decoded = html.unescape(page).replace("\\/", "/")

            candidates = re.findall(
                r"https://id\.eiga\.com/authorize/\?[^\s\"'<>]+",
                decoded
            )
            if not candidates:
                rel = re.findall(r"/authorize/\?[^\s\"'<>]+", decoded)
                candidates = [f"https://id.eiga.com{u}" for u in rel]

            if not candidates:
                return ""

            # state付きURLのみを許可（stateなしURLはcallback失敗を招きやすい）
            with_state = [u for u in candidates if re.search(r"[?&]state=[^&]+", u)]
            if not with_state:
                print("[DEBUG] ログインページHTMLに state付き認可URLが見つかりません")
                return ""
            chosen = with_state[0]
            chosen = self._normalize_oauth_callback_url(chosen)
            print(f"[DEBUG] ログインページHTMLから認可URLを抽出: {chosen}")
            try:
                parsed = urllib.parse.urlparse(chosen)
                qs = urllib.parse.parse_qs(parsed.query)
                state_val = qs.get("state", [None])[0]
                if state_val:
                    self.oauth_state = state_val
                    print(f"[DEBUG] 抽出した認可URLからstateを取得: {self.oauth_state}")
            except Exception:
                pass
            return chosen
        except Exception as e:
            print(f"[WARN] ログインページHTMLから認可URL抽出に失敗: {e}")
            return ""
    
    def login(self, email: str = None, password: str = None, _retry: int = 0) -> bool:
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
            time.sleep(1 if (email and password) else 3)
            
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
                    if not self.is_driver_alive():
                        print("[WARN] ログイン待機中にブラウザクローズを検出しました")
                        return False
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
            self.oauth_state = None
            self.user_id = None
            self.user_id_confirmed = False

            email_selectors = [
                (By.NAME, "email"),
                (By.CSS_SELECTOR, "input[type='email']"),
                (By.ID, "email"),
                (By.NAME, "mail"),
                (By.NAME, "mail_address"),
                (By.NAME, "mailaddress"),
                (By.NAME, "login_id"),
                (By.CSS_SELECTOR, "input[name*='mail']"),
                (By.CSS_SELECTOR, "input[autocomplete='username']"),
                (By.CSS_SELECTOR, "input[autocomplete='email']"),
                (By.CSS_SELECTOR, "input[placeholder*='メール']"),
            ]
            # 1) 現在ページ（/login/）でまず探索
            email_input = self._find_element_across_windows_and_frames(email_selectors, timeout=4)

            # 2) 見つからなければ、ログインページ内の正規OAuth導線をクリック
            if not email_input and self._open_authorize_via_login_page():
                email_input = self._find_element_across_windows_and_frames(email_selectors, timeout=8)

            # 3) まだ見つからなければ、OAuthエントリURLを直接開く
            if not email_input and self._open_oauth_entry_direct():
                email_input = self._find_element_across_windows_and_frames(email_selectors, timeout=8)

            # 4) まだ見つからなければ、ログインページHTMLから抽出した認可URLへ遷移
            if not email_input:
                extracted_auth_url = self._extract_authorize_url_from_login_page()
                if extracted_auth_url:
                    try:
                        print(f"[DEBUG] 抽出した認可URLへ遷移: {extracted_auth_url}")
                        self.driver.switch_to.default_content()
                        self.driver.get(extracted_auth_url)
                        time.sleep(1.5)
                    except Exception as nav_error:
                        print(f"[WARN] 抽出認可URLへの遷移に失敗: {nav_error}")
                    email_input = self._find_element_across_windows_and_frames(email_selectors, timeout=8)

            # 5) ここまでで見つからなければ失敗
            if not email_input:
                self._debug_dump_login_oauth_candidates()
                print("[WARN] メール入力フィールドを検出できませんでした")
                return False
            print("[DEBUG] メール入力フィールドが見つかりました")
            email_input.clear()
            email_input.send_keys(email)
            time.sleep(1)

            password_input = self._find_element_across_windows_and_frames([
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
                (By.ID, "password"),
                (By.NAME, "pass"),
                (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
                (By.CSS_SELECTOR, "input[placeholder*='パスワード']"),
            ], timeout=8)
            if not password_input:
                print("[WARN] パスワード入力フィールドを検出できませんでした")
                return False
            print("[DEBUG] パスワード入力フィールドが見つかりました")
            password_input.clear()
            password_input.send_keys(password)
            time.sleep(1)

            login_button = self._find_element_across_windows_and_frames([
                (By.XPATH, "//button[@type='submit']"),
                (By.XPATH, "//input[@type='submit']"),
                (By.XPATH, "//button[contains(., 'ログイン') or contains(., 'サインイン')]"),
                (By.CSS_SELECTOR, "button[class*='login']"),
            ], timeout=8)
            if not login_button:
                print("[WARN] ログインボタンを検出できませんでした")
                return False
            print("[DEBUG] ログインボタンをクリック")
            try:
                login_button.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", login_button)
            try:
                self.driver.switch_to.default_content()
            except Exception:
                pass
            
            # ログイン完了をポーリングで検証（最大 60 秒）
            max_wait = 60
            interval = 2
            waited = 0
            while waited < max_wait:
                if not self.is_driver_alive():
                    print("[WARN] 自動ログイン待機中にブラウザクローズを検出しました")
                    return False
                self._ensure_active_window()
                time.sleep(interval)
                waited += interval
                print(f"[DEBUG] 自動ログイン後待機 {waited}s")
                try:
                    current_url = self.driver.current_url
                except Exception:
                    current_url = ""

                if "/authorize/" in current_url.lower() and "/authorize/done" not in current_url.lower():
                    self._capture_state_from_dom()
                    try:
                        parsed = urllib.parse.urlparse(current_url)
                        qs = urllib.parse.parse_qs(parsed.query)
                        state_val = qs.get("state", [None])[0]
                        if state_val:
                            self.oauth_state = state_val
                    except Exception:
                        pass

                # /authorize/done で止まるケースがあるため、自動遷移処理を明示的に実行する
                if "/authorize/done" in current_url.lower():
                    print("[DEBUG] /authorize/done で停止中。マイページ遷移を試行します")
                    self._navigate_to_user_movie_page()
                    try:
                        current_url = self.driver.current_url
                    except Exception:
                        current_url = ""

                # user ページへ到達したら成功扱い
                if re.search(r"/user/[^/]+/", current_url):
                    self._extract_user_id(current_url)
                    if self.user_id:
                        self.user_id_confirmed = True
                    print(f"[DEBUG] 自動ログイン成功（user URL検出）: {current_url}")
                    return True

                if self.is_logged_in():
                    print("[DEBUG] 自動ログイン成功（ポーリング確認）")
                    # ユーザーIDを現在のURLから抽出
                    self._extract_user_id(current_url)
                    self._navigate_to_user_movie_page()
                    if self.user_id:
                        return True
                    print("[WARN] ログイン状態は検出したが user_id を取得できません。待機を継続します")
                    continue

                if self._is_logged_out_ui():
                    print("[WARN] eiga.com 側が未ログインUIのままです")
                    if _retry < 1:
                        print("[DEBUG] OAuthフローを再試行します")
                        try:
                            self.driver.get(self.AUTH_LOGIN_URL)
                            time.sleep(1)
                        except Exception:
                            pass
                        return self.login(email, password, _retry=_retry + 1)
                    return False

            print("[WARN] 自動ログイン後もログイン状態を確認できませんでした（タイムアウト）")
            return False
        
        except Exception as e:
            if self._is_browser_closed_error(e):
                self._mark_cancelled("ログイン処理中にブラウザが閉じられました")
                return False
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
        if not self.is_driver_alive():
            print("[WARN] 視聴履歴取得前にブラウザクローズを検出しました")
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
                        self._extract_user_id_from_page()
            
            # user URL で取得済みの場合は確定IDを優先し、不要な再遷移を避ける
            if not self.user_id_confirmed:
                if self.user_id:
                    print("[DEBUG] user_id は存在しますが未確定のため /mypage/ で確認します")
                    self._resolve_user_id_via_mypage()  # 失敗しても継続
                else:
                    if not self._resolve_user_id_via_mypage():
                        print("[ERROR] /mypage/ から user_id を確定できませんでした")
                        return []

            self._navigate_to_user_movie_page()

            if not self.user_id:
                print("[ERROR] ユーザーIDを取得できなかったため視聴履歴ページへ遷移できません")
                return []

            watched_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
            print(f"[DEBUG] 視聴済みページを取得: {watched_url}")
            
            # 最初のページへアクセス（URLパラメータで鑑賞済み抽出を固定）
            first_page_url = f"{watched_url}?sort=new&filter=watched&per=all&page=1"
            print(f"[DEBUG] 初回一覧URLへ遷移: {first_page_url}")
            self.driver.get(first_page_url)
            time.sleep(2)
            self._wait_for_movie_list_dom(timeout=15)
            
            movies = []
            page_num = 1
            max_pages = 1000  # 無限ループ防止
            
            while page_num <= max_pages:
                if not self.is_driver_alive():
                    print("[WARN] 視聴履歴取得中にブラウザクローズを検出しました")
                    return []
                page_url = f"{watched_url}?sort=new&filter=watched&per=all&page={page_num}"
                print(f"[DEBUG] ページ {page_num} を取得中: {page_url}")
                # フィルター設定後のURLを使用
                if page_num > 1:
                    self.driver.get(page_url)
                    self._wait_for_movie_list_dom(timeout=10)
                
                current_url = self.driver.current_url
                print(f"[DEBUG] 現在の URL: {current_url}")
                if not self.user_id:
                    self._extract_user_id(current_url)
                    if not self.user_id:
                        self._extract_user_id_from_page()
                
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # list-my-data div を探す（標準構造）
                movie_divs = soup.find_all('div', class_='list-my-data')
                print(f"[DEBUG] ページ {page_num}: list-my-data = {len(movie_divs)} 件")

                if not movie_divs:
                    # DOM描画待ち or パラメータ不足のケースに備え、per=all で再取得を試行
                    retry_urls = [
                        f"{watched_url}?sort=new&filter=watched&page={page_num}&per=all",
                        f"{watched_url}?sort=new&filter=watched&per=all",
                    ]
                    for retry_url in retry_urls:
                        print(f"[DEBUG] list-my-data 再取得を試行: {retry_url}")
                        self.driver.get(retry_url)
                        self._wait_for_movie_list_dom(timeout=10)
                        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                        movie_divs = soup.find_all('div', class_='list-my-data')
                        print(f"[DEBUG] 再取得結果 list-my-data = {len(movie_divs)} 件")
                        if movie_divs:
                            break
                
                if not movie_divs:
                    print("[WARN] list-my-data が見つからないため、リンクベース抽出へフォールバックします")
                    fallback_movies = self._parse_movie_links_fallback(soup)
                    print(f"[DEBUG] ページ {page_num}: fallback movies = {len(fallback_movies)} 件")
                    if not fallback_movies:
                        # 1回だけ一覧復旧導線を試して再評価
                        recovered = self._recover_movie_list_page()
                        if recovered:
                            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            movie_divs = soup.find_all('div', class_='list-my-data')
                            if movie_divs:
                                print(f"[DEBUG] 復旧後 list-my-data = {len(movie_divs)} 件")
                                for idx, div in enumerate(movie_divs):
                                    try:
                                        movie_data = self._parse_movie_div(div)
                                        if movie_data:
                                            movies.append(movie_data)
                                            print(f"[DEBUG] 映画 {len(movies)}: {movie_data.get('title')} を追加")
                                    except Exception as e:
                                        print(f"[WARN] 映画パースエラー (div {idx}): {e}")
                                        continue
                                # 復旧後は通常の次ページ判定へ進む
                            else:
                                fallback_movies = self._parse_movie_links_fallback(soup)
                                print(f"[DEBUG] 復旧後 fallback movies = {len(fallback_movies)} 件")
                                if fallback_movies:
                                    movies.extend(fallback_movies)
                                else:
                                    print("[WARN] このページに映画要素が見つかりません")
                                    break
                        else:
                            print("[WARN] このページに映画要素が見つかりません")
                            break
                    movies.extend(fallback_movies)
                else:
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
                next_link = soup.find('a', class_='next') or soup.find('a', attrs={'rel': 'next'})
                if next_link:
                    print("[DEBUG] 次ページリンクを検出。次ページへ移動します...")
                    page_num += 1
                else:
                    print("[DEBUG] 次ページリンクが見つかりません。最後のページです")
                    break
            
            print(f"[DEBUG] 合計 {len(movies)} 件の映画を取得")
            return movies
        
        except Exception as e:
            if self._is_browser_closed_error(e):
                self._mark_cancelled("視聴履歴取得中にブラウザが閉じられました")
                return []
            print(f"[ERROR] 視聴済み映画取得エラー: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_movie_links_fallback(self, soup) -> List[Dict]:
        """DOM差分時のフォールバック抽出。/movie/{id}/ リンクを基準に映画を抽出する。"""
        movies = []
        seen_ids = set()
        anchors = soup.find_all('a', href=re.compile(r'/movie/\d+/?'))
        for a in anchors:
            href = a.get('href') or ''
            m = re.search(r'/movie/(\d+)/?', href)
            if not m:
                continue
            external_id = m.group(1)
            if external_id in seen_ids:
                continue
            seen_ids.add(external_id)

            title = a.get_text(strip=True) or a.get('title', '').strip()
            if not title or len(title) < 2:
                continue

            movie_url = href if href.startswith('http') else (self.BASE_URL + href)
            parent = a.parent
            context_text = parent.get_text(" ", strip=True) if parent else ""

            released_year = None
            year_match = re.search(r'(19|20)\d{2}', context_text)
            if year_match:
                try:
                    released_year = int(year_match.group(0))
                except Exception:
                    released_year = None

            director = self._extract_director_from_text(context_text)

            movies.append({
                'title': title,
                'viewed_date': datetime.now(),
                'viewing_method': 'other',
                'rating': None,
                'movie_url': movie_url,
                'external_id': external_id,
                'image_url': None,
                'release_date': None,
                'released_year': released_year,
                'director': director
            })
        return movies

    def _extract_director_from_text(self, text: Optional[str]) -> Optional[str]:
        """
        監督名抽出（前置き/後置き両対応）
        例:
        - 監督：渡辺一貴
        - 渡辺一貴 監督
        """
        if not text:
            return None

        normalized = re.sub(r"\s+", " ", text).strip()

        # 前置き: 監督：渡辺一貴
        prefix = re.search(r'監督[：:\s]\s*([^/\n\r|]+)', normalized)
        if prefix:
            name = prefix.group(1).strip(" ・:：")
            if name:
                return name

        # 後置き: 渡辺一貴 監督
        suffix = re.search(r'([^/\n\r|]+?)\s*監督(?:\b|$)', normalized)
        if suffix:
            name = suffix.group(1).strip(" ・:：")
            if name and name != "監督":
                return name

        return None

    def _recover_movie_list_page(self) -> bool:
        """映画一覧要素が0件のとき、チェックイン作品ページへの再遷移を試す。"""
        try:
            # まず現在DOMから Myページ映画リンクを探索
            links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/user/') and contains(@href, '/movie/')]|"
                "//a[contains(@href, '/mypage/') and contains(., 'Myページ')]"
            )
            for link in links:
                href = link.get_attribute("href") or ""
                if "/user/" in href and "/movie/" in href:
                    retry_url = href
                    if "filter=watched" not in retry_url:
                        sep = "&" if "?" in retry_url else "?"
                        retry_url = f"{retry_url}{sep}sort=new&filter=watched&per=all"
                    print(f"[DEBUG] 一覧復旧遷移を試行: {retry_url}")
                    self.driver.get(retry_url)
                    time.sleep(2)
                    return True

            # 直接URLの最終フォールバック
            if self.user_id:
                retry_url = f"{self.BASE_URL}/user/{self.user_id}/movie/?sort=new&filter=watched&per=all"
                print(f"[DEBUG] 一覧復旧URLを直接試行: {retry_url}")
                self.driver.get(retry_url)
                time.sleep(2)
                return True
        except Exception as e:
            print(f"[WARN] 一覧復旧遷移に失敗: {e}")
        return False

    def _wait_for_movie_list_dom(self, timeout: int = 12) -> bool:
        """映画一覧DOM（list-my-data または /movie/{id}/ リンク）の描画を待機する。"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: (
                    len(BeautifulSoup(d.page_source, "html.parser").find_all("div", class_="list-my-data")) > 0
                    or bool(re.search(r"/movie/\d+/?", d.page_source))
                )
            )
            return True
        except Exception:
            return False
    
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
            released_year = None
            time_elem = div.find('small', class_='time')
            if time_elem:
                time_text = time_elem.get_text(strip=True)
                # 「劇場公開日：2023年5月26日」のような形式から抽出
                try:
                    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', time_text)
                    if date_match:
                        year, month, day = date_match.groups()
                        release_date = datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
                        released_year = int(year)
                except:
                    pass

            # サブテキスト（p.sub）から監督・年を抽出（空のときのみ詳細ページで補完）
            director = None
            sub_elem = div.find('p', class_='sub')
            if sub_elem:
                sub_text = sub_elem.get_text(" ", strip=True)
                if sub_text:
                    director = self._extract_director_from_text(sub_text)

                    if released_year is None:
                        year_match = re.search(r'(\d{4})年', sub_text)
                        if year_match:
                            try:
                                released_year = int(year_match.group(1))
                            except Exception:
                                released_year = None
            
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
                'release_date': release_date,
                'released_year': released_year,
                'director': director
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

            # ログインページURLは未ログイン扱い
            if re.search(r'/login/?', current_url.lower()) and 'oauth/gid' not in current_url.lower():
                print(f"[DEBUG] ログインURLのため未ログインと判定: {current_url}")
                return False

            if self._is_logged_out_ui():
                print("[DEBUG] 未ログインヘッダーを検出")
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
            # /user/{USER_KEY}/ パターンから user_id（数値・slug両対応）を抽出
            match = re.search(r'/user/([^/]+)/', url)
            if match:
                self.user_id = match.group(1)
                print(f"[DEBUG] ユーザーID を抽出しました: {self.user_id}")
            else:
                print(f"[DEBUG] ユーザーID パターンが見つかりません: {url}")
        except Exception as e:
            print(f"[WARN] ユーザーID 抽出エラー: {e}")

    def _resolve_user_id_via_mypage(self) -> bool:
        """`/mypage/` から自分の user_id を確定する。"""
        try:
            self._accept_alert_if_present()
            self.driver.get(self.BASE_URL + "/mypage/")
            time.sleep(2)
            self._accept_alert_if_present()
            if self._is_logged_out_ui():
                print("[WARN] /mypage/ が未ログイン画面へ遷移しました")
                return False
            page = self.driver.page_source

            # return_to はマイページ文脈のURLなので最優先で採用
            keys = re.findall(r'/user/([^/]+)/movie/', page)
            if not keys:
                cur = self.driver.current_url
                m = re.search(r'/user/([^/]+)/', cur)
                if m:
                    keys = [m.group(1)]

            if keys:
                best = Counter(keys).most_common(1)[0][0]
                self.user_id = best
                self.user_id_confirmed = True
                print(f"[DEBUG] /mypage/ から user_id を確定: {self.user_id}")
                return True
        except Exception as e:
            print(f"[WARN] /mypage/ から user_id 確定に失敗: {e}")
        return False

    def _extract_user_id_from_page(self) -> bool:
        """現在ページ内のリンクから user_id を抽出する。"""
        try:
            if self._is_logged_out_ui():
                print("[DEBUG] 未ログイン状態のため user_id 抽出をスキップ")
                return False
            page = self.driver.page_source
            soup = BeautifulSoup(page, 'html.parser')

            # 1) hidden return_to に含まれる user を最優先（自分のマイページ文脈）
            keys = []
            for inp in soup.find_all('input', attrs={'name': 'return_to'}):
                val = inp.get('value') or ''
                keys.extend(re.findall(r'/user/([^/]+)/', val))

            # 2) マイページ系リンクから候補収集
            for a in soup.select("div.mypage-link a[href], a[href='/mypage/'], a[href*='/user/'][title]"):
                href = a.get('href') or ''
                keys.extend(re.findall(r'/user/([^/]+)/', href))

            if keys:
                best = Counter(keys).most_common(1)[0][0]
                self.user_id = best
                print(f"[DEBUG] ページ内情報からユーザーIDを抽出しました: {self.user_id}")
                return True
        except Exception as e:
            print(f"[WARN] ページ内リンクからのユーザーID抽出エラー: {e}")
        return False
    
    def _navigate_to_user_movie_page(self) -> None:
        """
        ユーザーのマイページ（映画視聴履歴）へ遷移
        
        /authorize/done ページから自動的にマイページへ遷移します。
        ユーザーIDが設定されていない場合、リダイレクト後の URL から抽出します。
        """
        try:
            current_url = self.driver.current_url
            print(f"[DEBUG] _navigate_to_user_movie_page() 開始。現在URL: {current_url}")

            # 確定済み user_id の場合のみ、既に到達済み判定を許可
            if self.user_id_confirmed and self.user_id and re.search(rf'/user/{re.escape(self.user_id)}/', current_url):
                print(f"[DEBUG] 既にユーザーマイページにいます: {current_url}")
                return

            # /authorize/done ページにいる場合、univLink 等をクリックしてリダイレクトを待つ
            if '/authorize/done' in current_url.lower():
                print("[DEBUG] /authorize/done ページを検出。OAuth確定処理を試行します")
                done_url = self.driver.current_url
                self._capture_state_from_dom()

                def _wait_callback_settle(timeout_sec: float = 12.0):
                    waited = 0.0
                    while waited < timeout_sec:
                        self._ensure_active_window()
                        self._accept_alert_if_present()
                        try:
                            cur = self.driver.current_url
                        except Exception:
                            cur = ""
                        # id.eiga.com から抜けて、OAuthコールバックURLでもなくなれば確定
                        if cur and ("id.eiga.com" not in cur) and ("/login/oauth/gid/" not in cur):
                            return True
                        time.sleep(0.5)
                        waited += 0.5
                    return False

                # 戻るリンククリックを優先し、URL直叩きは行わない
                try:
                    callback_url = ""
                    wait_deadline = time.time() + 10
                    while time.time() < wait_deadline:
                        self._capture_state_from_dom()
                        callback_url = self._get_authorize_done_callback_url()
                        if (
                            callback_url
                            and re.search(r"[?&]code=[^&]+", callback_url)
                        ):
                            break
                        callback_url = ""
                        time.sleep(0.5)

                    if not callback_url:
                        print("[WARN] 戻るリンクの code を取得できませんでした")
                        return

                    print(f"[DEBUG] 映画.comへ戻るリンクを優先試行: {callback_url}")

                    links = self.driver.find_elements(By.CSS_SELECTOR, "div.row.link_btn a.univLink")
                    if not links:
                        links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/login/oauth/gid/') and contains(normalize-space(.), '映画.comへ戻る')]")

                    if links:
                        target = links[0]
                        raw_href = (target.get_attribute("href") or "").strip()
                        normalized_raw_href = self._normalize_oauth_callback_url(raw_href)
                        print(f"[DEBUG] 戻るリンク実href: {normalized_raw_href}")
                        if (
                            re.search(r"[?&]state=[^&]+", callback_url or "")
                            and not re.search(r"[?&]state=[^&]+", normalized_raw_href or "")
                        ):
                            try:
                                self.driver.execute_script("arguments[0].setAttribute('href', arguments[1]);", target, callback_url)
                                print("[DEBUG] 戻るリンクhrefを code+state へ上書きしました")
                            except Exception as e:
                                print(f"[WARN] 戻るリンクhref上書きに失敗: {e}")
                        try:
                            ActionChains(self.driver).move_to_element(target).pause(0.2).click(target).perform()
                            print("[DEBUG] 映画.comへ戻るリンクをクリックしました")
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", target)
                            print("[DEBUG] 映画.comへ戻るリンクを JS クリックしました")
                    else:
                        print("[WARN] 戻るリンク要素が見つからないため location.assign を使用します")
                        self.driver.execute_script("window.location.assign(arguments[0]);", callback_url)

                    _wait_callback_settle()
                    self._ensure_active_window()
                    alert_detected = self._accept_alert_if_present()
                    try:
                        cur = self.driver.current_url
                    except Exception:
                        cur = ""
                    if alert_detected:
                        print("[WARN] OAuth戻り処理で失敗アラートを検出しました")
                        return
                    if "/login/" in cur.lower():
                        print(f"[WARN] 戻るリンク後もログインページ: {cur}")
                        return
                    if self.is_logged_in():
                        self._extract_user_id(cur)
                        if self.user_id or self._resolve_user_id_via_mypage():
                            if self.user_id:
                                movie_page_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
                                print(f"[DEBUG] 戻るリンク経由でマイページへ遷移: {movie_page_url}")
                                self.driver.get(movie_page_url)
                                time.sleep(2)
                                return
                except Exception as e:
                    print(f"[WARN] 戻るリンク優先試行に失敗: {e}")

            # user_id が既にあれば直接遷移
            if self.user_id:
                movie_page_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
                print(f"[DEBUG] ユーザマイページへ直接遷移: {movie_page_url}")
                self.driver.get(movie_page_url)
                time.sleep(2)
                return

            # /mypage/ 直遷移で user_id 補完を試す（最優先）
            try:
                print("[DEBUG] user_id 未取得のため /mypage/ 直遷移を試行します")
                self.driver.get(self.BASE_URL + "/mypage/")
                time.sleep(2)
                self._extract_user_id(self.driver.current_url)
                if not self.user_id:
                    self._extract_user_id_from_page()
                if self.user_id:
                    movie_page_url = f"{self.BASE_URL}/user/{self.user_id}/movie/"
                    print(f"[DEBUG] /mypage/ 経由でマイページへ遷移: {movie_page_url}")
                    self.driver.get(movie_page_url)
                    time.sleep(2)
                    return
            except Exception as e:
                print(f"[WARN] /mypage/ 経由の user_id 補完に失敗: {e}")

            print("[WARN] user_id を取得できなかったため、自動遷移をスキップします")

        except Exception as e:
            if self._is_browser_closed_error(e):
                self._mark_cancelled("マイページ遷移中にブラウザが閉じられました")
                return
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
            if self._is_browser_closed_error(e):
                self._mark_cancelled("フィルター設定中にブラウザが閉じられました")
                return
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
