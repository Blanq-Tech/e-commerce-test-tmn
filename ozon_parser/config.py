"""Конфигурация приложения. Тащим всё из окружения, чтобы ничего не хардкодить."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Подхватываем .env, если он лежит рядом с проектом.
load_dotenv()


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip())
    except (TypeError, ValueError):
        return default


# Несколько правдоподобных десктопных User-Agent'ов — крутим их по кругу,
# чтобы воркеры не выглядели как один и тот же клиент.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]


@dataclass(slots=True)
class Settings:
    """Все настройки прогона в одном месте."""

    proxy_server: str | None = field(default_factory=lambda: os.getenv("OZON_PROXY") or None)
    proxy_ignore_https: bool = field(default_factory=lambda: _bool("PROXY_IGNORE_HTTPS", True))
    proxies_file: str = field(default_factory=lambda: os.getenv("PROXIES_FILE", "proxies.txt"))
    proxy_cooldown_sec: int = field(default_factory=lambda: _int("PROXY_COOLDOWN_SEC", 90))

    headless: bool = field(default_factory=lambda: _bool("HEADLESS", True))
    concurrency: int = field(default_factory=lambda: _int("CONCURRENCY", 3))
    max_position: int = field(default_factory=lambda: _int("MAX_POSITION", 100))

    min_delay_ms: int = field(default_factory=lambda: _int("MIN_DELAY_MS", 600))
    max_delay_ms: int = field(default_factory=lambda: _int("MAX_DELAY_MS", 1800))
    max_retries: int = field(default_factory=lambda: _int("MAX_RETRIES", 3))

    nav_timeout_ms: int = field(default_factory=lambda: _int("NAV_TIMEOUT_MS", 45000))
    locale: str = field(default_factory=lambda: os.getenv("LOCALE", "ru-RU"))
    timezone: str = field(default_factory=lambda: os.getenv("TIMEZONE", "Europe/Moscow"))

    output_dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "output")))

    # Офлайн-режим: путь к сохранённой странице выдачи (file://...) для
    # детерминированной проверки логики без обращения к живому Ozon.
    fixture: str | None = field(default_factory=lambda: os.getenv("OZON_FIXTURE") or None)

    def proxy_config(self) -> dict | None:
        """Playwright ждёт прокси словарём; поддерживаем логин/пароль в URL."""
        if not self.proxy_server:
            return None
        from urllib.parse import urlsplit

        parts = urlsplit(self.proxy_server)
        server = f"{parts.scheme}://{parts.hostname}"
        if parts.port:
            server += f":{parts.port}"
        cfg: dict[str, str] = {"server": server}
        if parts.username:
            cfg["username"] = parts.username
        if parts.password:
            cfg["password"] = parts.password
        return cfg



