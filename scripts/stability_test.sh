#!/usr/bin/env bash
# Часть 2. Устойчивость: 3 прогона подряд с интервалом 30 секунд.
# Все три запуска должны вернуть результат (не ошибку и не блокировку).
set -euo pipefail

QUERY="${QUERY:-нож туристический}"
SKU="${SKU:-1635725435}"
RUNS="${RUNS:-3}"
INTERVAL="${INTERVAL:-30}"

echo "=== Тест устойчивости: '${QUERY}' / sku=${SKU}, прогонов=${RUNS}, пауза=${INTERVAL}с ==="

ok=0
for i in $(seq 1 "${RUNS}"); do
  echo ""
  echo "----- Прогон ${i}/${RUNS} ($(date '+%H:%M:%S')) -----"
  if python main.py --query "${QUERY}" --sku "${SKU}"; then
    ok=$((ok + 1))
    echo ">>> Прогон ${i}: УСПЕХ"
  else
    echo ">>> Прогон ${i}: сбой (код $?)"
  fi
  if [ "${i}" -lt "${RUNS}" ]; then
    echo "...пауза ${INTERVAL}с..."
    sleep "${INTERVAL}"
  fi
done

echo ""
echo "=== Итог: ${ok}/${RUNS} прогонов успешно ==="
[ "${ok}" -eq "${RUNS}" ]

