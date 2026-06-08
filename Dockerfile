# Готовый образ с Chromium и всеми системными зависимостями Playwright.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

# Сначала зависимости — лучше кешируется слой.
COPY pyproject.toml ./
RUN pip install --no-cache-dir playwright>=1.44 python-dotenv>=1.0

# Код проекта.
COPY ozon_parser ./ozon_parser
COPY main.py ./
COPY data ./data

# Папка под результаты.
RUN mkdir -p output

ENV HEADLESS=true \
    PROXIES_FILE=/app/proxies.txt \
    OUTPUT_DIR=/app/output \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "main.py"]

