"""Оркестрация: пул асинхронных воркеров поверх одного браузера."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from .browser import BrowserManager
from .config import Settings
from .logger import get_logger
from .models import SearchResult, SearchTask
from .proxy import ProxyPool
from .search import SearchParser

log = get_logger("orchestrator")


class Orchestrator:
    """Раздаёт задачи воркерам, ограничивая параллелизм семафором.

    Один браузер на процесс, N одновременных контекстов (по числу воркеров).
    Это и есть «многопоточность» в асинхронном мире: пока один воркер ждёт
    сеть, другие работают.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sem = asyncio.Semaphore(settings.concurrency)
        self.pool = ProxyPool.from_file(settings.proxies_file, settings.proxy_cooldown_sec)
        # перемешиваем, чтобы воркеры стартовали с разных IP
        self.pool.shuffle()

    async def _worker(self, parser: SearchParser, task: SearchTask) -> SearchResult:
        async with self._sem:
            log.info("→ старт: query=%r sku=%s", task.query, task.sku)
            started = time.monotonic()
            result = await parser.run(task)
            elapsed = time.monotonic() - started
            log.info(
                "← готово: sku=%s позиция=%s статус=%s (%.1fс)",
                task.sku, result.position, result.status, elapsed,
            )
            return result

    async def run(self, tasks: list[SearchTask]) -> list[SearchResult]:
        if not tasks:
            return []
        log.info(
            "Запускаю %d задач, параллелизм=%d, глубина=%d, прокси в пуле=%d",
            len(tasks), self.settings.concurrency, self.settings.max_position, len(self.pool),
        )
        async with BrowserManager(self.settings) as manager:
            parser = SearchParser(manager, self.settings, self.pool)
            coros = [self._worker(parser, t) for t in tasks]
            results = await asyncio.gather(*coros, return_exceptions=False)
        return list(results)

    def save(self, results: list[SearchResult]) -> Path:
        out_dir = self.settings.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"results_{int(time.time())}.json"
        payload = [r.to_dict() for r in results]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("Результаты сохранены: %s", path)
        return path




