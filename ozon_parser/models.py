"""Модели данных: задача на проверку и результат."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class SearchTask:
    """Одна единица работы: ищем `sku` по запросу `query`."""

    query: str
    sku: str

    @property
    def key(self) -> str:
        return f"{self.query}::{self.sku}"


@dataclass(slots=True)
class SearchResult:
    """Результат проверки позиции — ровно тот JSON, что нужен в задании."""

    query: str
    sku: str
    position: int | str  # номер 1..N либо "not_found"
    page: int | None
    total_checked: int
    timestamp: str
    status: str = "ok"  # ok | not_found | error | blocked
    error: str | None = None

    @classmethod
    def make(
        cls,
        task: SearchTask,
        position: int | None,
        page: int | None,
        total_checked: int,
        status: str = "ok",
        error: str | None = None,
    ) -> "SearchResult":
        return cls(
            query=task.query,
            sku=task.sku,
            position=position if position is not None else "not_found",
            page=page,
            total_checked=total_checked,
            timestamp=datetime.now().astimezone().replace(microsecond=0).isoformat(),
            status=status if position is not None or status != "ok" else "not_found",
            error=error,
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        # error не выводим, если его нет — чтобы JSON был чистым
        if self.error is None:
            data.pop("error")
        return data

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

