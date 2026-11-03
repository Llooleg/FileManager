# =============================================================================
# Dockerfile приложения secfm (FileManager)
# Многостадийная сборка: минимальный итоговый образ + непривилегированный юзер.
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 · builder — компиляция исходников и проверка импортируемости
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build
# корень репозитория сам является пакетом -> кладём его как /build/pkg/FileManager
COPY . /build/pkg/FileManager

RUN python -m compileall -q /build/pkg/FileManager \
 && PYTHONPATH=/build/pkg python -c "import FileManager, FileManager.cli, FileManager.serve"

# ---------------------------------------------------------------------------
# Stage 2 · runtime — только скомпилированный код, без инструментария сборки
# ---------------------------------------------------------------------------
FROM python:3.12-slim

# непривилегированный пользователь для запуска приложения
RUN groupadd --system app \
 && useradd --system --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /build/pkg /app

# каталог данных (SQLite-БД и песочницы пользователей) в volume
RUN mkdir -p /data/workspace && chown -R app:app /data

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

USER app
VOLUME /data
EXPOSE 8000

# health: обслуживает FileManager.serve (см. serve.py)
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["python", "-m", "FileManager.serve"]
