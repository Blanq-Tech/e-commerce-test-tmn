"""Пул прокси с ротацией и временным баном «уставших» адресов."""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from .logger import get_logger

log = get_logger("proxy")


@dataclass(slots=True)
class Proxy:
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    # до какого момента (monotonic) прокси выведен из ротации после ошибки
    blocked_until: float = 0.0

    @classmethod
    def parse(cls, line: str) -> "Proxy":
        """Разбираем строку формата host:port[:user:pass]."""
        parts = line.strip().split(":")
        if len(parts) == 2:
            host, port = parts
            return cls(host=host, port=int(port))
        if len(parts) == 4:
            host, port, user, pwd = parts
            return cls(host=host, port=int(port), username=user, password=pwd)
        raise ValueError(f"Не понимаю строку прокси: {line!r}")

    @property
    def label(self) -> str:
        return f"{self.host}:{self.port}"

    def to_playwright(self) -> dict:
        cfg: dict[str, str] = {"server": f"http://{self.host}:{self.port}"}
        if self.username:
            cfg["username"] = self.username
        if self.password:
            cfg["password"] = self.password
        return cfg


class ProxyPool:
    """Потокобезопасный пул: выдаёт живой прокси, баним сбойные на cooldown."""

    def __init__(self, proxies: list[Proxy], cooldown_sec: int = 90) -> None:
        self._proxies = proxies
        self._cooldown = cooldown_sec
        self._lock = threading.Lock()
        self._cursor = 0

    @classmethod
    def from_file(cls, path: str | Path, cooldown_sec: int = 90) -> "ProxyPool":
        p = Path(path)
        if not p.exists():
            log.warning("Файл прокси не найден: %s — работаем без пула", p)
            return cls([], cooldown_sec)
        proxies: list[Proxy] = []
        for raw in p.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if not raw or raw.startswith("#"):
                continue
            try:
                proxies.append(Proxy.parse(raw))
            except ValueError as exc:
                log.warning("Пропускаю строку прокси: %s", exc)
        log.info("Загружено прокси: %d", len(proxies))
        return cls(proxies, cooldown_sec)

    def __len__(self) -> int:
        return len(self._proxies)

    @property
    def enabled(self) -> bool:
        return bool(self._proxies)

    def acquire(self) -> Proxy | None:
        """Берём следующий живой прокси по кругу. None, если пул пуст."""
        if not self._proxies:
            return None
        now = time.monotonic()
        with self._lock:
            n = len(self._proxies)
            for _ in range(n):
                proxy = self._proxies[self._cursor % n]
                self._cursor += 1
                if proxy.blocked_until <= now:
                    return proxy
            # все в бане — берём наименее «протухший» и надеемся
            proxy = min(self._proxies, key=lambda p: p.blocked_until)
            log.warning("Все прокси на cooldown, форсирую %s", proxy.label)
            return proxy

    def mark_bad(self, proxy: Proxy | None) -> None:
        if proxy is None:
            return
        with self._lock:
            proxy.blocked_until = time.monotonic() + self._cooldown
        log.info("Прокси %s в бане на %dс", proxy.label, self._cooldown)

    def shuffle(self) -> None:
        with self._lock:
            random.shuffle(self._proxies)

