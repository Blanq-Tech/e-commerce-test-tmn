"""CLI-обёртка: принимает запрос+артикул или файл с задачами."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .config import Settings
from .logger import setup_logging
from .models import SearchResult, SearchTask
from .orchestrator import Orchestrator


def _load_tasks(args: argparse.Namespace) -> list[SearchTask]:
    if args.tasks:
        raw = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
        return [SearchTask(query=item["query"], sku=str(item["sku"])) for item in raw]
    if args.query and args.sku:
        return [SearchTask(query=args.query, sku=str(args.sku))]
    raise SystemExit("Нужно указать либо --query и --sku, либо --tasks <file.json>")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ozon-rank",
        description="Поиск позиции товара (SKU) в выдаче Ozon.",
    )
    p.add_argument("--query", help="поисковый запрос")
    p.add_argument("--sku", help="артикул товара")
    p.add_argument("--tasks", help="JSON-файл со списком задач [{query, sku}, ...]")
    p.add_argument("--concurrency", type=int, help="число параллельных воркеров")
    p.add_argument("--max-position", type=int, help="глубина проверки (по умолчанию 100)")
    p.add_argument("--headful", action="store_true", help="показать окно браузера")
    p.add_argument("--no-save", action="store_true", help="не сохранять файл с результатами")
    return p


async def _run(args: argparse.Namespace) -> list[SearchResult]:
    settings = Settings()
    if args.concurrency:
        settings.concurrency = args.concurrency
    if args.max_position:
        settings.max_position = args.max_position
    if args.headful:
        settings.headless = False

    tasks = _load_tasks(args)
    orchestrator = Orchestrator(settings)
    results = await orchestrator.run(tasks)
    if not args.no_save:
        orchestrator.save(results)
    return results


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    results = asyncio.run(_run(args))

    # В stdout — чистый JSON, как требует задание.
    out = [r.to_dict() for r in results]
    print(json.dumps(out if len(out) > 1 else out[0], ensure_ascii=False, indent=2))

    # Код возврата: 0 если все ok/not_found, 1 если были ошибки.
    return 0 if all(r.status in {"ok", "not_found"} for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())

