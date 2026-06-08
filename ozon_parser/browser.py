"""Управление браузером Playwright: один движок на процесс, изолированные контексты на воркеров."""
from __future__ import annotations

import itertools
import random

from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright

from .config import USER_AGENTS, Settings
from .logger import get_logger

log = get_logger("browser")

# Небольшой скрипт-«заглушка», который прячет самые очевидные следы автоматизации.
# Полноценный stealth тут не нужен, но navigator.webdriver и пустой plugins выдают бота сразу.
_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || {runtime: {}};
"""


class BrowserManager:
    """Поднимает Chromium и раздаёт изолированные контексты.

    Один Browser шарится между воркерами (это дёшево), а вот контекст —
    свой на каждую задачу: отдельные куки, кеш и «личность».
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._ua_cycle = itertools.cycle(USER_AGENTS)

    async def __aenter__(self) -> "BrowserManager":
        self._pw = await async_playwright().start()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]
        self._browser = await self._pw.chromium.launch(
            headless=self.settings.headless,
            args=launch_args,
            proxy=self.settings.proxy_config(),
        )
        log.info(
            "Браузер запущен (headless=%s, proxy=%s)",
            self.settings.headless,
            self.settings.proxy_config().get("server") if self.settings.proxy_config() else "нет",
        )
        return self

    async def __aexit__(self, *exc) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        log.info("Браузер остановлен")

    async def new_context(self) -> BrowserContext:
        assert self._browser is not None, "Браузер не запущен"
        ua = next(self._ua_cycle)
        context = await self._browser.new_context(
            user_agent=ua,
            locale=self.settings.locale,
            timezone_id=self.settings.timezone,
            viewport={"width": random.randint(1280, 1680), "height": random.randint(800, 1000)},
            ignore_https_errors=self.settings.proxy_ignore_https,
            extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8"},
        )
        context.set_default_navigation_timeout(self.settings.nav_timeout_ms)
        context.set_default_timeout(self.settings.nav_timeout_ms)
        await context.add_init_script(_STEALTH_JS)
        return context

