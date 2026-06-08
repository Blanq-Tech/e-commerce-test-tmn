"""Парсер поисковой выдачи Ozon поверх Playwright."""
from __future__ import annotations

import asyncio
import random
from urllib.parse import quote

from playwright.async_api import BrowserContext, Page, TimeoutError as PWTimeout

from .browser import BrowserManager
from .config import Settings
from .extract import extract_skus, find_position, page_of
from .logger import get_logger
from .models import SearchResult, SearchTask

log = get_logger("search")

SEARCH_URL = "https://www.ozon.ru/search/?text={query}&from_global=true&page={page}"

# Маркеры страницы-заглушки антибота Ozon.
BLOCK_MARKERS = (
    "Доступ ограничен",
    "Access denied",
    "you have been blocked",
    "Проверка безопасности",
    "/block.html",
)

# Селекторы товарных плиток. Ozon периодически их меняет, поэтому держим несколько.
TILE_SELECTORS = (
    "a[href*='/product/']",
)


class BlockedError(RuntimeError):
    """Антибот показал заглушку вместо выдачи."""


class SearchParser:
    """Открывает поиск, листает страницы и считает позицию артикула."""

    def __init__(self, manager: BrowserManager, settings: Settings) -> None:
        self.manager = manager
        self.settings = settings

    async def _human_pause(self) -> None:
        delay = random.randint(self.settings.min_delay_ms, self.settings.max_delay_ms) / 1000
        await asyncio.sleep(delay)

    async def _looks_blocked(self, page: Page) -> bool:
        try:
            content = await page.content()
        except Exception:
            return False
        return any(marker in content for marker in BLOCK_MARKERS)

    async def _collect_page_hrefs(self, page: Page) -> list[str]:
        """Собираем ссылки на товары в порядке их следования в DOM."""
        # Немного скроллим, чтобы подгрузилась ленивая верстка.
        for _ in range(6):
            await page.mouse.wheel(0, 2200)
            await asyncio.sleep(0.4)
        hrefs: list[str] = []
        for selector in TILE_SELECTORS:
            found = await page.eval_on_selector_all(
                selector, "els => els.map(e => e.getAttribute('href'))"
            )
            hrefs.extend(h for h in found if h)
            if hrefs:
                break
        return hrefs

    async def _open_search_page(self, context: BrowserContext, query: str, page_num: int) -> Page:
        page = await context.new_page()
        url = SEARCH_URL.format(query=quote(query), page=page_num)
        await page.goto(url, wait_until="domcontentloaded")
        if await self._looks_blocked(page):
            await page.close()
            raise BlockedError(f"Антибот на странице поиска (page={page_num})")
        try:
            await page.wait_for_selector(TILE_SELECTORS[0], timeout=self.settings.nav_timeout_ms)
        except PWTimeout:
            # Возможно, это снова заглушка — проверим перед тем, как сдаться.
            if await self._looks_blocked(page):
                await page.close()
                raise BlockedError("Антибот: плитки не появились")
        return page

    async def _scan_once(self, task: SearchTask) -> SearchResult:
        """Одна полная попытка: свежий контекст, проход по страницам выдачи."""
        context = await self.manager.new_context()
        collected: list[str] = []
        pages_needed = (self.settings.max_position // 36) + 1
        try:
            for page_num in range(1, pages_needed + 1):
                page = await self._open_search_page(context, task.query, page_num)
                hrefs = await self._collect_page_hrefs(page)
                await page.close()

                before = len(collected)
                collected = extract_skus(collected_to_hrefs(collected) + hrefs)
                log.info(
                    "[%s] стр.%d: +%d товаров (всего %d)",
                    task.sku, page_num, len(collected) - before, len(collected),
                )

                pos = find_position(collected, task.sku)
                if pos is not None:
                    return SearchResult.make(
                        task, position=pos, page=page_of(pos), total_checked=len(collected)
                    )
                if len(collected) >= self.settings.max_position:
                    break
                if not hrefs:
                    break
                await self._human_pause()

            checked = min(len(collected), self.settings.max_position)
            return SearchResult.make(task, position=None, page=None, total_checked=checked,
                                     status="not_found")
        finally:
            await context.close()

    async def run(self, task: SearchTask) -> SearchResult:
        """Запускает задачу с ретраями на блокировки/сбои."""
        last_error: str | None = None
        for attempt in range(1, self.settings.max_retries + 1):
            try:
                result = await self._scan_once(task)
                return result
            except BlockedError as exc:
                last_error = str(exc)
                log.warning("[%s] попытка %d: блокировка (%s)", task.sku, attempt, exc)
            except PWTimeout as exc:
                last_error = f"timeout: {exc}"
                log.warning("[%s] попытка %d: таймаут", task.sku, attempt)
            except Exception as exc:  # noqa: BLE001 — наверх не роняем, фиксируем как error
                last_error = repr(exc)
                log.exception("[%s] попытка %d: неожиданная ошибка", task.sku, attempt)
            # экспоненциальный бэкофф с джиттером
            await asyncio.sleep(min(2 ** attempt, 30) + random.random())

        return SearchResult.make(task, position=None, page=None, total_checked=0,
                                 status="error", error=last_error)


def collected_to_hrefs(skus: list[str]) -> list[str]:
    """Обратное преобразование SKU -> псевдо-ссылка, чтобы не терять порядок при слиянии."""
    return [f"/product/-{sku}" for sku in skus]

