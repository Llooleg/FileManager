#!/bin/sh
# Health-check приложения после локального деплоя (Stage 4).
#
# Вынесен в отдельный скрипт, а не inline-блок в YAML, чтобы:
#   1) не ломать парсер Bash у правил Semgrep yaml.github-actions.*
#      (metavariable-pattern падал на многострочном if с продолжением "\");
#   2) скрипт можно было запускать/тестировать локально без конвейера.
#
# Использование: sh healthcheck.sh [контейнер] [порт]
set -eu

CONTAINER="${1:-filemanager-ci}"
PORT="${2:-8000}"
ATTEMPTS=15
DELAY=2

i=1
while [ "$i" -le "$ATTEMPTS" ]; do
    if docker exec "$CONTAINER" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$PORT/health', timeout=2)"; then
        echo "Приложение отвечает на /health — деплой успешен."
        exit 0
    fi
    echo "Попытка $i/$ATTEMPTS: приложение ещё не готово, ждём ${DELAY}s..."
    i=$((i + 1))
    sleep "$DELAY"
done

echo "Приложение не поднялось за $((ATTEMPTS * DELAY)) сек. Логи контейнера:"
docker logs "$CONTAINER" || true
exit 1
