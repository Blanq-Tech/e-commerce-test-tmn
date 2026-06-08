# Ozon Rank Parser

Асинхронный многопоточный парсер позиций товаров в поисковой выдаче Ozon на **Playwright**.
По паре «поисковый запрос + артикул (SKU)» определяет позицию товара в выдаче (1–100)
и отдаёт результат в JSON.

## Что делает

- Принимает запрос и SKU (через CLI или файл задач).
- Открывает поиск Ozon реальным браузером (Chromium), листает выдачу.
- Находит позицию товара по артикулу или возвращает `not_found`.
- Работает параллельно (пул асинхронных воркеров) с оркестрацией и ретраями.
- Ходит через пул прокси с ротацией и баном «спалившихся» IP.

Формат вывода:

```json
{
  "query": "нож туристический",
  "sku": "1635725435",
  "position": 17,
  "page": 1,
  "total_checked": 100,
  "timestamp": "2026-03-20T14:30:00+03:00",
  "status": "ok"
}
```

`status`: `ok` | `not_found` | `error`.

## Архитектура (кратко)

```
CLI ──► Orchestrator ──► [worker × N] ──► SearchParser ──► Playwright (Chromium)
                 │                              │
            ProxyPool (ротация)          extract.py (разбор SKU)
```

- `config.py` — настройки из окружения/`.env`.
- `proxy.py` — пул прокси: парсинг `host:port:user:pass`, round-robin, cooldown.
- `browser.py` — запуск Chromium, изолированный контекст на воркера, лёгкий stealth.
- `extract.py` — чистые функции разбора ссылок и поиска позиции (покрыты тестами).
- `search.py` — открытие выдачи, пагинация, сбор SKU, ретраи и смена прокси.
- `orchestrator.py` — семафор-пул воркеров поверх одного браузера, сохранение JSON.

Подробнее — в [architecture.md](architecture.md). Лог разработки — в [approach.md](approach.md).

## Установка

Требуется Python 3.10+.

```bash
pip install playwright python-dotenv
python -m playwright install chromium
```

Либо через Poetry:

```bash
poetry install
poetry run python -m playwright install chromium
```

## Настройка прокси

Скопируйте пример и впишите свои прокси (по одному в строке, `host:port:user:pass`):

```bash
cp proxies.example.txt proxies.txt
```

`proxies.txt` в `.gitignore` — секреты в репозиторий не попадают.
Параметры окружения — в `.env` (см. `.env.example`).

## Запуск

Один запрос:

```bash
python main.py --query "нож туристический" --sku 1635725435
```

Пакет задач из файла:

```bash
python main.py --tasks data/tasks.example.json --concurrency 3
```

Полезные флаги: `--max-position 100`, `--headful` (показать окно), `--no-save`.

Результаты дублируются в `output/results_<ts>.json`.

## Тесты

```bash
python -m pytest -q
```

Покрыты чистые функции: разбор SKU из ссылок, поиск позиции, ротация и бан прокси.

## Docker

```bash
docker compose build
docker compose run --rm parser --query "нож туристический" --sku 1635725435
```

Тест устойчивости (Часть 2) — 3 прогона с паузой 30с:

```bash
docker compose run --rm stability
```

## Тестовые данные

В `data/tasks.example.json` — 3 запроса и 3 SKU из категории «туризм/дом»
(нож туристический, термокружка, палатка). Категории выбраны как стабильные:
много товаров, выдача глубокая (легко проверять позиции до 100), запросы
не сезонные и не персонализированные.

## Что работает / что нет

- ✅ Логика разбора выдачи и поиска позиции, оркестрация, ротация прокси, ретраи — покрыто тестами.
- ✅ Запуск в Docker, тест устойчивости 3/3.
- ⚠️ Ozon агрессивно фингерпринтит трафик (антибот «fab»). Подробный разбор всех
  упёртостей и обходов — в [approach.md](approach.md). Под нагрузкой обязателен
  пул качественных резидентных прокси; датацентровые IP выгорают быстро.

