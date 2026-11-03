# Локальный запуск CI/CD (GitHub Actions + act)

Конвейер описан в [`.github/workflows/main.yml`](.github/workflows/main.yml)
и полностью соответствует спецификациям в `Specs/`.

## Стадии конвейера

| Стадия | Джоба | Что делает | Артефакты |
|---|---|---|---|
| Stage 1 · Build | `build` | Компиляция исходников и сборка `FileManager-<sha>.pyz` в контейнере `python:3.12` | `build-dist` (.pyz) |
| Stage 2 · Test | `test` | Smoke-тест артефакта из Stage 1, unit-тесты с отчётами **JUnit XML** и **Cobertura XML** | `test-reports` |
| Stage 3 · Security | `security` | SAST-сканер **Semgrep** (`p/default`); находки **High/Critical роняют сборку** (гейт `.github/scripts/semgrep_gate.py`) | `semgrep-report` |
| Stage 4 · Deploy | `deploy` | Сборка Docker-образа (multi-stage Dockerfile), **локальный запуск с пробросом порта 8080→8000**, health-check | `docker-image` (`.tar.gz`) |

Все шаги выполняются в изолированных Docker-контейнерах (`container:`),
поэтому результат не зависит от ОС раннера. Зависимости кэшируются
(`~/.cache/pip`), данные между стадиями передаются артефактами.

## 1. Подготовка локального раннера

Нужен Docker (Docker Desktop, colima и т.п.) и утилита [act](https://github.com/nektos/act):

```sh
# macOS
brew install act

# Linux
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
```

## 2. Секреты

Секреты передаются **только через переменные окружения** и не хранятся в коде:

```sh
cp .secrets.example .secrets   # .secrets в .gitignore, коммитить нельзя
$EDITOR .secrets               # SEMGREP_APP_TOKEN, APP_SECRET
```

`act` подхватывает `.secrets` автоматически. Для работы конвейера токены
необязательны (есть безопасные значения по умолчанию для локального запуска).

## 3. Запуск конвейера локально

```sh
# целиком (все стадии по цепочке needs: build -> test -> security -> deploy)
act -P ubuntu-latest=catthehacker/ubuntu:act-latest

# одна стадия
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j build
act -P ubuntu-latest=catthehacker/ubuntu:act-latest -j security

# посмотреть список джоб
act -l
```

> **Stage 4 (Deploy)** монтирует Docker-сокет хоста
> (`/var/run/docker.sock`) в контейнер джобы — это работает с Docker
> Desktop / локальным dockerd. После запуска проверьте:
> `curl http://localhost:8080/health`.
>
> **Stage 3 (Semgrep)** скачивает конфиг `p/default` из сети — нужен интернет.

## 4. Запуск на github.com

Пуш в репозиторий запускает конвейер автоматически. Джобы Build/Test/Security
работают и на стандартных раннерах GitHub. Джоба **Deploy** требует Docker-сокет,
поэтому для неё нужен **self-hosted раннер** с установленным Docker
(Settings → Actions → Runners → New self-hosted runner).

Артефакты каждой стадии скачиваются на странице запуска:
Actions → выбранный run → Artifacts.

## 5. Ручная работа с Docker-образом

```sh
docker build -t filemanager:local .

# сервис здоровья (порт 8000 внутри контейнера)
docker run -d --name fm -p 8080:8000 -e APP_SECRET="secret" filemanager:local
curl http://localhost:8080/health

# интерактивный CLI файлового менеджера (данные — в volume /data)
docker run -it --rm -v fm-data:/data -w /data filemanager:local python -m FileManager

# восстановление образа из артефакта конвейера
docker load < filemanager-image.tar.gz
```

Образ собирается multi-stage (builder → slim runtime), приложение внутри
работает от непривилегированного пользователя `app`.
