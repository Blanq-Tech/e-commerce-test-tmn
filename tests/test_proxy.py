"""Тесты пула прокси: парсинг, ротация, бан/cooldown."""
import time

from ozon_parser.proxy import Proxy, ProxyPool


def test_parse_with_auth():
    p = Proxy.parse("45.139.168.143:8000:UBETgP:3JeXNx")
    assert p.host == "45.139.168.143"
    assert p.port == 8000
    assert p.username == "UBETgP"
    assert p.password == "3JeXNx"
    assert p.to_playwright() == {
        "server": "http://45.139.168.143:8000",
        "username": "UBETgP",
        "password": "3JeXNx",
    }


def test_parse_without_auth():
    p = Proxy.parse("1.2.3.4:8000")
    assert p.to_playwright() == {"server": "http://1.2.3.4:8000"}


def test_round_robin_rotation():
    pool = ProxyPool([Proxy.parse(f"10.0.0.{i}:8000") for i in range(1, 4)])
    seen = [pool.acquire().label for _ in range(3)]
    assert seen == ["10.0.0.1:8000", "10.0.0.2:8000", "10.0.0.3:8000"]
    # пошли по кругу
    assert pool.acquire().label == "10.0.0.1:8000"


def test_mark_bad_skips_proxy():
    pool = ProxyPool([Proxy.parse("10.0.0.1:8000"), Proxy.parse("10.0.0.2:8000")],
                     cooldown_sec=60)
    first = pool.acquire()
    pool.mark_bad(first)
    # следующий живой не должен быть забаненным
    nxt = pool.acquire()
    assert nxt.label != first.label
    assert first.blocked_until > time.monotonic()


def test_empty_pool_returns_none():
    pool = ProxyPool([])
    assert pool.acquire() is None
    assert pool.enabled is False

