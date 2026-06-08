"""Тесты разбора ссылок и поиска позиции — без браузера."""
from ozon_parser.extract import (
    extract_skus,
    find_position,
    page_of,
    parse_sku_from_href,
)


def test_parse_sku_from_slug_href():
    href = "/product/krossovki-nike-air-1635725435/?asb=abc"
    assert parse_sku_from_href(href) == "1635725435"


def test_parse_sku_from_plain_id():
    assert parse_sku_from_href("/product/1396122168") == "1396122168"


def test_parse_sku_from_sku_param():
    assert parse_sku_from_href("/category/x/?sku=1521234567&z=1") == "1521234567"


def test_parse_sku_none_for_garbage():
    assert parse_sku_from_href("/category/nozhi/") is None
    assert parse_sku_from_href("") is None


def test_extract_skus_keeps_order_and_dedup():
    hrefs = [
        "/product/a-111111/",
        "/product/b-222222/",
        "/product/a-111111/?utm=1",  # дубль
        "/category/none/",
        "/product/c-333333/",
    ]
    assert extract_skus(hrefs) == ["111111", "222222", "333333"]


def test_find_position():
    skus = ["111111", "222222", "333333"]
    assert find_position(skus, "222222") == 2
    assert find_position(skus, "999999") is None
    # сравнение по строке, даже если передали число
    assert find_position(skus, 333333) == 3


def test_page_of():
    assert page_of(1) == 1
    assert page_of(36) == 1
    assert page_of(37) == 2
    assert page_of(100, page_size=36) == 3

