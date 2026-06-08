#!/usr/bin/env bash
# Деплой на сервер ТОЛЬКО через git (без rsync).
# Схема: на сервере поднимаем bare-репозиторий, пушим в нег�� по SSH,
# затем выкладываем рабочее дерево через `git checkout`.
#
# Использование:
#   bash scripts/deploy.sh            # хост по умолчанию: blanq
#   HOST=blanq bash scripts/deploy.sh
set -euo pipefail

HOST="${HOST:-blanq}"
BARE="${BARE:-/root/ozon-rank.git}"     # bare-репозиторий на сервере
WORK="${WORK:-/root/ozon-rank}"         # рабочее дерево на сервере
BRANCH="${BRANCH:-main}"

echo "==> Готовлю bare-репозиторий на ${HOST}:${BARE}"
ssh "${HOST}" "git init --bare ${BARE} >/dev/null 2>&1 || true"

echo "==> Настраиваю git-remote 'deploy'"
git remote remove deploy 2>/dev/null || true
git remote add deploy "${HOST}:${BARE}"

echo "==> Пушу ветку ${BRANCH} на сервер"
git push deploy "${BRANCH}" --force

echo "==> Раскладываю рабочее дерево на сервере (${WORK})"
ssh "${HOST}" "mkdir -p ${WORK} && git --git-dir=${BARE} --work-tree=${WORK} checkout -f ${BRANCH} && ls -la ${WORK}"

echo "==> Готово. Код на сервере: ${HOST}:${WORK}"
echo "    Дальше на сервере: положить proxies.txt, собрать docker и запустить."

