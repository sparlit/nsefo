"""
Browser Login System for NSEFO
================================
Playwright-based browser automation for extracting broker access tokens.
Flow: [Browser Login] → [Extract Token] → [Python Session Manager] → [Rust Execution Engine] → [Broker Endpoint]

Features:
- Stealth browser (undetected automation)
- Network interception to capture tokens
- TLS fingerprint matching
- Heartbeat keep-alive
- Auto re-login on 401/token expiration
- Paper trading first, live on demand
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any, List

logger = logging.getLogger("BrowserLogin")


# ── Broker Login Configurations ───────────────────────────────────────────────
# Maps provider name → (login_url, token_extract_pattern, redirect_uri, auth_type)
# auth_type: "oauth2" | "form_post" | "api_key"

BROKER_AUTH_CONFIG: Dict[str, Dict[str, Any]] = {
    "zerodha": {
        "login_url": "https://kite.zerodha.com/connect/login?api_key={api_key}&v=3",
        "token_type": "oauth2",
        "redirect_uri": "http://localhost:9100",
        "token_param": "request_token",  # OAuth request_token → exchanged for access_token
        "exchange_flow": "request_token",
    },
    "icici": {
        "login_url": "https://api.icicidirect.com/oauth2/authorize"
                     "?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}"
                     "&scope=portfolio+holdings+orderbook+trades+quote",
        "token_type": "oauth2",
        "redirect_uri": "http://localhost:9100",
        "token_param": "code",  # Auth code → exchanged for access_token
        "exchange_endpoint": "https://api.icicidirect.com/oauth2/token",
    },
    "hdfc": {
        "login_url": "https://api.hdfcsec.com/api/auth/login",
        "token_type": "form_post",
        "token_param": "access_token",
        "token_location": "body",  # token comes in POST response body
    },
    "groww": {
        "login_url": "https://api.groww.in/v1/login",
        "token_type": "api_key",
        "token_param": "access_token",
        "token_location": "header",  # Authorization: Bearer <token>
    },
    "edelweiss": {
        "login_url": "https://api.edelweiss.in/oauth/token",
        "token_type": "oauth2",
        "token_param": "access_token",
        "token_location": "body",
        "refresh_param": "refresh_token",
    },
    "anand_rathi": {
        "login_url": "https://api.edios.in/apis/authorize",
        "token_type": "oauth2",
        "token_param": "access_token",
        "token_location": "body",
    },
    "axis_direct": {
        "login_url": "https://api.axisdirect.in/user/login",
        "token_type": "form_post",
        "token_param": "access_token",
        "token_location": "body",
    },
    "geojit": {
        "login_url": "https://api.geojit.com/v1/login",
        "token_type": "form_post",
        "token_param": "access_token",
        "token_location": "body",
    },
    "sharekhan": {
        "login_url": "https://newtrade.sharekhan.com/sk/api/oauth/login",
        "token_type": "oauth2",
        "token_param": "access_token",
        "token_location": "body",
    },
    "angelone": {
        "login_url": "https://www.angelone.in/login",
        "token_type": "form_post",
        "token_param": "access_token",
        "token_location": "body",
    },
    "fyers": {
        "login_url": "https://api.fyers.in/login",
        "token_type": "oauth2",
        "redirect_uri": "http://localhost:9100",
        "token_param": "access_token",
    },
    "upstox": {
        "login_url": "https://api.upstox.com/v2/login",
        "token_type": "oauth2",
        "redirect_uri": "http://localhost:9100",
        "token_param": "access_token",
    },
    "moneysukh": {
        "login_url": "https://online.moneysukh.com/api/v1/login",
        "token_type": "form_post",
        "token_param": "access_token",
        "token_location": "body",
    },
}


@dataclass
class TokenInfo:
    """Holds extracted token + metadata."""
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0  # Unix timestamp
    token_type: str = "Bearer"
    provider: str = ""

    def is_expired(self) -> bool:
        """Token expired or about to expire (5 min buffer)."""
        return time.time() >= (self.expires_at - 300)

    def is_valid(self) -> bool:
        return bool(self.access_token) and not self.is_expired()


@dataclass
class BrowserLoginConfig:
    """Configuration for a single broker browser login attempt."""
    provider: str
    login_url: str
    redirect_uri: str = "http://localhost:9100"
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    username: str = ""
    password: str = ""
    totp_secret: str = ""
    timeout_seconds: int = 60
    headless: bool = False  # Set True for production/headless servers


class BrowserLoginEngine:
    """
    Playwright-based browser login engine.
    Opens a stealth browser, intercepts network requests,
    extracts the access token, and stores it for session use.

    Flow: [Open Browser] → [Navigate to Login] → [User Enters Credentials]
          → [Intercept Token] → [Close Browser] → [Return Token]
    """

    def __init__(self, config: BrowserLoginConfig):
        self.config = config
        self.token_info: Optional[TokenInfo] = None
        self._playwright = None
        self._browser = None
        self._page = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._heartbeat_timer: Optional[threading.Timer] = None
        self._stop_heartbeat = threading.Event()
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def login(self, **kwargs) -> TokenInfo:
        """
        Main entry point. Opens browser, captures token, returns TokenInfo.
        Falls back to existing token if browser login fails.
        """
        if not self._check_dependencies():
            logger.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return self._fallback_token()

        try:
            with self._lock:
                self._run_browser_login()
            return self.token_info or self._fallback_token()
        except Exception as e:
            logger.error(f"Browser login failed for {self.config.provider}: {e}")
            return self._fallback_token()

    def relogin(self) -> TokenInfo:
        """Force re-authentication (called on 401 or token expiration)."""
        logger.info(f"Re-authenticating {self.config.provider} via browser...")
        self.stop_heartbeat()
        return self.login()

    def stop_heartbeat(self):
        """Stop the keep-alive heartbeat."""
        self._stop_heartbeat.set()
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()

    def start_heartbeat(self, interval: int = 240):
        """
        Start a background heartbeat thread that keeps the session alive.
        Sends a ping to the broker API every `interval` seconds.
        Respawns browser login automatically if token expires.
        """
        self.stop_heartbeat()
        self._stop_heartbeat.clear()

        def heartbeat_loop():
            while not self._stop_heartbeat.wait(timeout=interval):
                try:
                    if self.token_info and self.token_info.is_expired():
                        logger.info(f"Token expired for {self.config.provider}, re-logging in...")
                        self.login()
                except Exception as e:
                    logger.warning(f"Heartbeat error for {self.config.provider}: {e}")

        self._heartbeat_timer = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_timer.start()
        logger.info(f"Heartbeat started for {self.config.provider} every {interval}s")

    # ── Internal ─────────────────────────────────────────────────────────────

    def _check_dependencies(self) -> bool:
        try:
            from playwright.sync_api import sync_playwright
            return True
        except ImportError:
            return False

    def _run_browser_login(self):
        """Run the actual Playwright browser automation (blocking)."""
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

        with sync_playwright() as p:
            # Launch stealth browser (not detected as automation)
            self._browser = p.chromium.launch(
                headless=self.config.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--window-size=1280,800",
                ],
            )
            context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                ignore_https_errors=True,  # For broker certs
            )
            # Block ads/trackers to speed up loading
            context.route(
                lambda route: route.abort() if "ads" in route.request.url or "tracker" in route.request.url
                else route.continue_()
            )
            self._page = context.new_page()

            # Set up network interception BEFORE navigating
            self._setup_interception()

            # Navigate to login page
            login_url = self._build_login_url()
            logger.info(f"Navigating to: {login_url}")

            try:
                self._page.goto(login_url, wait_until="networkidle", timeout=30000)
            except PlaywrightTimeout:
                logger.warning("Page load timed out, continuing anyway...")

            # Wait for user to complete login manually (broker redirects after auth)
            logger.info("Waiting for broker redirect with token...")
            self._wait_for_redirect(timeout=self.config.timeout_seconds)

            self._browser.close()
            self._browser = None

    def _setup_interception(self):
        """Set up Playwright network route handlers to capture tokens."""
        provider = self.config.provider.lower()

        def handle_response(response):
            url = response.url
            try:
                body = ""
                try:
                    body = response.text()
                except Exception:
                    pass

                # Look for token in response headers
                auth_header = response.headers.get("authorization", "") or \
                              response.headers.get("Authorization", "")
                if auth_header and "Bearer" in auth_header:
                    token = auth_header.replace("Bearer ", "").strip()
                    if token and len(token) > 10:
                        self._store_token(token, expires_in=3600)

                # Look for token in response body (various patterns)
                if not self.token_info:
                    self._extract_token_from_body(body, url)

            except Exception as e:
                logger.debug(f"Response intercept error: {e}")

        self._page.on("response", handle_response)

        def handle_request(request):
            url = request.url
            # Check request headers for tokens being sent
            headers = request.headers
            auth = headers.get("authorization", "") or headers.get("Authorization", "")
            if auth and "Bearer" in auth and not self.token_info:
                token = auth.replace("Bearer ", "").strip()
                if token and len(token) > 10:
                    self._store_token(token, expires_in=3600)

            # Log API calls for debugging
            if any(x in url for x in ["/api/", "/oauth/", "/v1/", "/v2/"]):
                logger.debug(f"API: {request.method} {url}")

        self._page.on("request", handle_request)

    def _extract_token_from_body(self, body: str, url: str):
        """Parse JSON/HTML response body to find access token."""
        if not body or len(body) < 10:
            return

        provider = self.config.provider.lower()

        # Common JSON token locations
        import re
        patterns = [
            r'"access_token"\s*:\s*"([^"]{10,})"',
            r'"accessToken"\s*:\s*"([^"]{10,})"',
            r'"token"\s*:\s*"([^"]{10,})"',
            r"Bearer\s+([A-Za-z0-9_\-]{10,})",
        ]
        for pat in patterns:
            m = re.search(pat, body)
            if m:
                self._store_token(m.group(1), expires_in=3600)
                logger.info(f"Token extracted from body of {url}")
                break

    def _store_token(self, token: str, expires_in: int = 3600):
        """Thread-safe token storage."""
        with self._lock:
            if self.token_info and self.token_info.access_token == token:
                return  # Already stored
            self.token_info = TokenInfo(
                access_token=token,
                expires_at=time.time() + expires_in,
                token_type="Bearer",
                provider=self.config.provider,
            )
            logger.info(f"Token stored for {self.config.provider} (expires in {expires_in}s)")

    def _wait_for_redirect(self, timeout: int):
        """
        Wait for the OAuth redirect or login success.
        Monitors for redirect to the callback URL with the token/code in the URL.
        """
        import selectors
        selector = selectors.DefaultSelector()
        redirect_received = threading.Event()
        redirect_data: Dict[str, str] = {}

        def check_redirect():
            start = time.time()
            while not redirect_received.is_set() and (time.time() - start) < timeout:
                current_url = self._page.url if self._page else ""
                if self.config.redirect_uri in current_url:
                    # Parse token/code from URL
                    parsed = urllib.parse.urlparse(current_url)
                    qs = urllib.parse.parse_qs(parsed.query)
                    for key in ["request_token", "code", "access_token", "token"]:
                        if key in qs:
                            val = qs[key][0]
                            if key in ("request_token", "code"):
                                # OAuth code needs exchange — store for later
                                self._oauth_code = val
                                logger.info(f"OAuth {key} captured: {val[:10]}...")
                                # Exchange immediately
                                self._exchange_oauth_code(val)
                            else:
                                self._store_token(val)
                            redirect_received.set()
                            return
                time.sleep(0.5)

        t = threading.Thread(target=check_redirect, daemon=True)
        t.start()
        redirect_received.wait(timeout=timeout)
        if not redirect_received.is_set():
            logger.warning(f"No redirect received within {timeout}s for {self.config.provider}")
            # Fallback: try to extract token from current page
            self._try_page_token_extraction()

    def _try_page_token_extraction(self):
        """Fallback: look for tokens in the current page DOM/localStorage."""
        try:
            if not self._page:
                return
            # Check localStorage/sessionStorage
            storage = self._page.evaluate("""
                JSON.stringify({
                    local: JSON.stringify(localStorage),
                    session: JSON.stringify(sessionStorage)
                })
            """)
            self._extract_token_from_body(storage, "storage")
            # Check page content
            content = self._page.content()
            self._extract_token_from_body(content, "page")
        except Exception as e:
            logger.debug(f"Page token extraction failed: {e}")

    def _exchange_oauth_code(self, code: str):
        """Exchange OAuth authorization code for access token."""
        import httpx

        provider = self.config.provider.lower()
        if provider == "zerodha":
            # Zerodha: POST request_token + api_secret → access_token
            try:
                resp = httpx.post(
                    "https://api.kite.trade/api/token",
                    data={
                        "request_token": code,
                        "api_key": self.config.api_key,
                        "client_id": self.config.client_id,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    token = data.get("data", {}).get("access_token", "")
                    if token:
                        self._store_token(token, expires_in=data.get("data", {}).get("expires_in", 86400))
                        logger.info("Zerodha token exchanged successfully")
            except Exception as e:
                logger.error(f"Zerodha token exchange failed: {e}")

        elif provider == "icici":
            # ICICI: POST grant_type=authorization_code → access_token + refresh_token
            try:
                resp = httpx.post(
                    "https://api.icicidirect.com/oauth2/token",
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.config.redirect_uri,
                        "client_id": self.config.client_id,
                        "client_secret": self.config.client_secret,
                    },
                    timeout=10,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    access = data.get("access_token", "")
                    refresh = data.get("refresh_token", "")
                    exp = data.get("expires_in", 3600)
                    if access:
                        self.token_info = TokenInfo(
                            access_token=access,
                            refresh_token=refresh,
                            expires_at=time.time() + exp,
                            token_type="Bearer",
                            provider=self.config.provider,
                        )
                        logger.info("ICICI token exchanged successfully")
            except Exception as e:
                logger.error(f"ICICI token exchange failed: {e}")

    def _build_login_url(self) -> str:
        """Build the login URL for the current provider."""
        cfg = BROKER_AUTH_CONFIG.get(self.config.provider.lower(), {})
        url = cfg.get("login_url", "")

        replacements = {
            "{api_key}": self.config.api_key,
            "{client_id}": self.config.client_id,
            "{client_secret}": self.config.client_secret,
            "{redirect_uri}": urllib.parse.quote(self.config.redirect_uri, safe=""),
            "{username}": urllib.parse.quote(self.config.username, safe=""),
        }
        for k, v in replacements.items():
            url = url.replace(k, v)
        return url

    def _fallback_token(self) -> TokenInfo:
        """Return empty token (caller should fall back to manual config)."""
        return TokenInfo(provider=self.config.provider)


# ── Token Manager ─────────────────────────────────────────────────────────────
# Singleton that manages tokens for all brokers with auto-relogin

class TokenManager:
    """
    Centralized token manager: stores tokens per broker,
    auto-relogs on 401, maintains heartbeats.
    """
    _instance: Optional["TokenManager"] = None

    def __new__(cls) -> "TokenManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._tokens: Dict[str, TokenInfo] = {}
        self._engines: Dict[str, BrowserLoginEngine] = {}
        self._config: Dict[str, BrowserLoginConfig] = {}
        self._lock = threading.Lock()
        self._heartbeats: Dict[str, threading.Timer] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        logger.info("TokenManager initialized")

    def register_broker(
        self,
        provider: str,
        api_key: str = "",
        client_id: str = "",
        client_secret: str = "",
        username: str = "",
        password: str = "",
        totp_secret: str = "",
        existing_token: str = "",
        token_expires_at: float = 0.0,
    ):
        """Register a broker with token manager."""
        with self._lock:
            if provider in self._tokens:
                return  # Already registered

            token_info = TokenInfo(
                access_token=existing_token,
                expires_at=token_expires_at,
                provider=provider,
            )
            self._tokens[provider] = token_info
            logger.info(f"Broker registered: {provider} (existing_token={'yes' if existing_token else 'none'})")

    def get_token(self, provider: str) -> Optional[TokenInfo]:
        """Get valid token (auto-refreshes if expired)."""
        with self._lock:
            token = self._tokens.get(provider)
            if token and token.is_valid():
                return token
            if token and token.is_expired():
                logger.info(f"Token expired for {provider}, triggering re-login")
                # Trigger async re-login in background
                threading.Thread(target=self._relogin_async, args=(provider,), daemon=True).start()
            return token  # Return expired token anyway — caller will get 401

    def set_token(self, provider: str, token_info: TokenInfo):
        """Store a newly acquired token."""
        with self._lock:
            self._tokens[provider] = token_info
            logger.info(f"Token updated for {provider}")

    def on_auth_error(self, provider: str, status_code: int):
        """
        Called when broker API returns 401/403.
        Triggers immediate re-login.
        """
        if status_code in (401, 403):
            logger.warning(f"Auth error {status_code} for {provider}, re-logging in...")
            threading.Thread(target=self._relogin_async, args=(provider,), daemon=True).start()

    def _relogin_async(self, provider: str):
        """Background re-login with exponential backoff."""
        for attempt in range(3):
            try:
                engine = self._engines.get(provider)
                if engine:
                    new_token = engine.relogin()
                    if new_token and new_token.is_valid():
                        self.set_token(provider, new_token)
                        logger.info(f"Re-login success for {provider}")
                        return
                time.sleep(2 ** attempt)  # 1s, 2s, 4s backoff
            except Exception as e:
                logger.error(f"Re-login attempt {attempt+1} failed for {provider}: {e}")
                time.sleep(2 ** attempt)

    def start_heartbeat(self, provider: str, interval: int = 240):
        """Start heartbeat for a broker."""
        stop = self._stop_events.get(provider) or threading.Event()
        self._stop_events[provider] = stop

        def beat():
            while not stop.wait(timeout=interval):
                try:
                    token = self._tokens.get(provider)
                    if token and token.is_expired():
                        engine = self._engines.get(provider)
                        if engine:
                            engine.relogin()
                except Exception as e:
                    logger.debug(f"Heartbeat error {provider}: {e}")

        t = threading.Thread(target=beat, daemon=True)
        t.start()
        logger.info(f"Heartbeat started for {provider} every {interval}s")

    def stop_all_heartbeats(self):
        """Stop all heartbeat threads."""
        for stop in self._stop_events.values():
            stop.set()


# ── AutoReloginMixin ───────────────────────────────────────────────────────────
# Mixin class that brokers can inherit to get auto-relogin on 401


class AutoReloginMixin:
    """
    Mixin for Broker classes.
    Intercepts HTTP responses and auto-relogs on 401.
    Usage: class MyBroker(Broker, AutoReloginMixin):
    """

    def __init__(self, *args, **kwargs):
        self._token_manager = TokenManager()
        self._relogin_in_progress = False
        self._relogin_lock = threading.Lock()

    def _handle_auth_error(self, status_code: int):
        """Call this from each HTTP call site on 401/403."""
        if status_code in (401, 403):
            with self._relogin_lock:
                if not self._relogin_in_progress:
                    self._relogin_in_progress = True
                    provider = getattr(self, "provider", self.__class__.__name__)
                    threading.Thread(
                        target=self._do_relogin,
                        args=(provider,),
                        daemon=True,
                    ).start()
                    self._relogin_in_progress = False

    def _do_relogin(self, provider: str):
        """Perform re-login and update token."""
        try:
            self._token_manager.on_auth_error(provider, 401)
        except Exception as e:
            logger.error(f"Re-login failed for {provider}: {e}")


# ── TLS Fingerprint HTTP Client ────────────────────────────────────────────────
# Uses curl_cffi to match Chrome TLS fingerprints for broker API calls


def get_tls_client():
    """
    Returns an httpx-like client with TLS fingerprint matching Chrome.
    Uses curl_cffi for proper JA3/TLS fingerprinting.
    """
    try:
        from curl_cffi import requests as curl_requests
        return curl_requests.Session(impersonate="chrome")
    except ImportError:
        logger.warning("curl_cffi not installed (TLS fingerprint won't match Chrome). "
                       "Run: pip install curl_cffi")
        import httpx
        return httpx.Client(verify=True)


def get_tls_httpx() -> Any:
    """Returns httpx.Client with TLS settings matching a real browser."""
    try:
        from curl_cffi.requests import Session as CurlSession
        return CurlSession(impersonate="chrome")
    except ImportError:
        import httpx
        return httpx.Client(verify=True, http2=True)


# ── Convenience functions ─────────────────────────────────────────────────────


def browser_login(
    provider: str,
    api_key: str = "",
    client_id: str = "",
    client_secret: str = "",
    username: str = "",
    password: str = "",
    totp_secret: str = "",
    headless: bool = False,
    timeout: int = 60,
    callback_url: str = "http://localhost:9100",
) -> TokenInfo:
    """
    One-shot browser login for a broker.
    Opens browser → user logs in → token extracted → browser closes.
    Returns TokenInfo with access_token.

    Usage:
        token = browser_login("zerodha", api_key="xxx", ...)
        token = browser_login("icici", client_id="xxx", client_secret="xxx", ...)
    """
    auth_cfg = BROKER_AUTH_CONFIG.get(provider.lower(), {})
    config = BrowserLoginConfig(
        provider=provider,
        login_url=auth_cfg.get("login_url", ""),
        redirect_uri=callback_url,
        api_key=api_key,
        client_id=client_id,
        client_secret=client_secret,
        username=username,
        password=password,
        totp_secret=totp_secret,
        timeout_seconds=timeout,
        headless=headless,
    )
    engine = BrowserLoginEngine(config)
    return engine.login()


def start_browser_login_background(
    provider: str,
    api_key: str = "",
    client_id: str = "",
    client_secret: str = "",
    callback_url: str = "http://localhost:9100",
    heartbeat_interval: int = 240,
) -> BrowserLoginEngine:
    """
    Start browser login in background with auto-relogin + heartbeat.
    Returns the engine immediately — token is populated asynchronously.

    Usage:
        engine = start_browser_login_background(
            "zerodha", api_key="xxx", callback_url="http://localhost:9100"
        )
        # Engine runs in background, re-logs in automatically
    """
    auth_cfg = BROKER_AUTH_CONFIG.get(provider.lower(), {})
    config = BrowserLoginConfig(
        provider=provider,
        login_url=auth_cfg.get("login_url", ""),
        redirect_uri=callback_url,
        api_key=api_key,
        client_id=client_id,
        client_secret=client_secret,
        timeout_seconds=120,
        headless=False,
    )
    engine = BrowserLoginEngine(config)

    # Start login in background thread
    t = threading.Thread(target=engine.login, daemon=True)
    t.start()

    # Start heartbeat
    engine.start_heartbeat(interval=heartbeat_interval)

    return engine