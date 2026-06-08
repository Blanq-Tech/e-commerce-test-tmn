"""Чистые функции разбора — без браузера, легко покрыть тестами."""
from __future__ import annotations

import re
from urllib.parse import unquote

# /product/krossovki-nike-1234567890/  -> 1234567890
# /product/1234567890                  -> 1234567890
# также ловим ?...&sku=123 на всякий случай
_PRODUCT_RE = re.compile(r"/product/(?:[^/?#]*?-)?(\d{5,})")
_SKU_PARAM_RE = re.compile(r"[?&]sku=(\d{5,})")


def parse_sku_from_href(href: str) -> str | None:
    """Достаём артикул (SKU) из ссылки на товар."""
    if not href:
        return None
    href = unquote(href)
    m = _PRODUCT_RE.search(href)
    if m:
        return m.group(1)
    m = _SKU_PARAM_RE.search(href)
    if m:
        return m.group(1)
    return None


def extract_skus(hrefs: list[str]) -> list[str]:
    """Превращаем список ссылок в упорядоченный список уникальных SKU.

    Порядок — как на странице (это и есть позиция в выдаче),
    дубликаты выкидываем, сохраняя первое вхождение.
    """
    seen: set[str] = set()
    ordered: list[str] = []
    for href in hrefs:
        sku = parse_sku_from_href(href)
        if sku and sku not in seen:
            seen.add(sku)
            ordered.append(sku)
    return ordered


def find_position(skus: list[str], target_sku: str) -> int | None:
    """Позиция товара в выдаче (1-based) или None, если не нашли."""
    target = str(target_sku).strip()
    for idx, sku in enumerate(skus, start=1):
        if sku == target:
            return idx
    return None


def page_of(position: int, page_size: int = 36) -> int:
    """По абсолютной позиции прикидываем номер страницы выдачи."""
    if position < 1:
        return 1
    return (position - 1) // page_size + 1

