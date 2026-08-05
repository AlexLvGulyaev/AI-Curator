# AI Curator — Руководство по развёртыванию

## Назначение

Единый Source of Truth для воспроизведения работоспособного экземпляра AI Curator в чистом окружении. Если после выполнения руководства система не работает, руководство устарело.

Руководство рассчитано на технически подготовленного пользователя, знакомого с Docker, Linux и базовой работой DNS.

## Варианты развёртывания

| Вариант | Когда использовать | Публичные домены | Требования |
|---|---|---|---|
| **Локальный запуск** | Первое знакомство, разработка, локальное тестирование | Не нужны | Docker + Docker Compose |
| **Production на VPS** | Публичный demo, пилот, production | Нужны 4 домена | VPS, DNS, Traefik, SSL |

> **Важно:** все примеры доменов, токенов и паролей в этом документе — плейсхолдеры. Никогда не используйте значения из примеров в production.

---

## Общие требования

- Linux, macOS или Windows с WSL2.
- Установленные Docker Engine и Docker Compose plugin.
- Клонированный репозиторий:

```bash
git clone https://github.com/AlexLvGulyaev/AI-Curator.git
cd AI-Curator
```

---

## Вариант 1. Локальный запуск

Локальный запуск не требует публичных доменов, DNS и Traefik. Сервисы доступны по портам на `localhost`.

### 1.1. Подготовка `.env`

Создайте файл `.env` в корне репозитория:

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://ai_curator:YOUR_DB_PASSWORD@ai-curator-postgres:5432/ai_curator
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini-2024-07-18
CHROMA_HOST=ai-curator-chroma
CHROMA_PORT=8000

# LMS integration
LMS_BASE_URL=http://localhost:8080
LMS_API_TOKEN=YOUR_MOODLE_WEBSERVICE_TOKEN

# Admin Console auth
ADMIN_CONSOLE_URL=http://localhost:3001
ADMIN_CONSOLE_TOKEN=YOUR_RANDOM_HEX_TOKEN_64_CHARS
ADMIN_CONSOLE_DEMO_TOKEN=YOUR_DEMO_READONLY_TOKEN_64_CHARS

# Web UI
WEB_UI_URL=http://localhost:3000

# Demo mode
DEMO_ENABLED=true
DEMO_MAX_REQUESTS_PER_SESSION=20
DEMO_SESSION_TTL_MINUTES=30
DEMO_RATE_LIMIT_PER_MINUTE=12
DEMO_MAX_SESSIONS_PER_IP_PER_HOUR=5
DEMO_CACHE_TTL_SECONDS=604800

# Log retention
ARCHIVE_DIR=/app/storage/archives
HOT_RETENTION_DAYS=30
TRACE_RETENTION_DAYS=7

# KB Content Git
KB_CONTENT_GIT_ENABLED=true
KB_CONTENT_REPO_PATH=/app/kb-content
KB_CONTENT_REPO_URL=
KB_CONTENT_SSH_KEY_PATH=
KB_CONTENT_DEFAULT_BRANCH=main

# Moodle (embedded stack)
MOODLE_DB_USER=moodle
MOODLE_DB_PASSWORD=YOUR_MOODLE_DB_PASSWORD
MOODLE_DB_NAME=moodle
MOODLE_ADMIN_USER=admin
MOODLE_ADMIN_PASSWORD=YOUR_MOODLE_ADMIN_PASSWORD
MOODLE_ADMIN_EMAIL=admin@example.com
MOODLE_SITE_NAME="AI Curator Demo LMS"
```

### 1.2. Создание `docker-compose.override.yml`

Для локального запуска создайте `docker-compose.override.yml` в корне репозитория:

```yaml
services:
  ai-curator-lms:
    environment:
      MOODLE_WWWROOT: http://localhost:8080
    labels: []
    ports:
      - "8080:80"
    networks:
      - ai-curator-network

  ai-curator-backend:
    ports:
      - "8000:8000"

  ai-curator-web-ui:
    ports:
      - "3000:80"

  ai-curator-admin-console:
    ports:
      - "3001:80"
```

Этот файл переопределяет production-метки Traefik и открывает порты локально.

### 1.3. Запуск

```bash
docker compose up --build -d
```

### 1.4. Проверка локального развёртывания

```bash
# Health backend
curl -s http://localhost:8000/health
# Expected: {"status":"ok","service":"ai-curator-backend"}

# Moodle доступен на http://localhost:8080
# Web UI на http://localhost:3000
# Admin Console на http://localhost:3001
```

---

## Вариант 2. Production на VPS

### 2.1. Подготовка инфраструктуры

1. Арендуйте VPS с Docker и Docker Compose.
2. Зарегистрируйте 4 домена (или поддомена) и направьте A-записи на IP сервера:

```text
ai-curator.example.com      → Веб-интерфейс
ai-curator-admin.example.com → Консоль администратора
ai-curator-api.example.com    → Backend API
lms.example.com               → Moodle LMS
```

3. Установите и настройте Traefik с Let's Encrypt. Пример минимальной конфигурации Traefik:

```yaml
# traefik/traefik.yml
global:
  sendAnonymousUsage: false

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

certificatesResolvers:
  myresolver:
    acme:
      email: admin@example.com
      storage: /letsencrypt/acme.json
      tlsChallenge: {}

providers:
  docker:
    exposedByDefault: false
    network: n8n_default
```

Создайте сеть `n8n_default`:

```bash
docker network create n8n_default
```

### 2.2. Подготовка `.env`

Замените `example.com` на ваши реальные домены и заполните секреты:

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://ai_curator:YOUR_DB_PASSWORD@ai-curator-postgres:5432/ai_curator
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini-2024-07-18
CHROMA_HOST=ai-curator-chroma
CHROMA_PORT=8000

# LMS integration
LMS_BASE_URL=https://lms.example.com
LMS_API_TOKEN=YOUR_MOODLE_WEBSERVICE_TOKEN

# Admin Console auth
ADMIN_CONSOLE_URL=https://ai-curator-admin.example.com
ADMIN_CONSOLE_TOKEN=YOUR_RANDOM_HEX_TOKEN_64_CHARS
ADMIN_CONSOLE_DEMO_TOKEN=YOUR_DEMO_READONLY_TOKEN_64_CHARS

# Web UI
WEB_UI_URL=https://ai-curator.example.com

# Demo mode
DEMO_ENABLED=true
DEMO_MAX_REQUESTS_PER_SESSION=20
DEMO_SESSION_TTL_MINUTES=30
DEMO_RATE_LIMIT_PER_MINUTE=12
DEMO_MAX_SESSIONS_PER_IP_PER_HOUR=5
DEMO_CACHE_TTL_SECONDS=604800

# Log retention
ARCHIVE_DIR=/app/storage/archives
HOT_RETENTION_DAYS=30
TRACE_RETENTION_DAYS=7

# KB Content Git
KB_CONTENT_GIT_ENABLED=true
KB_CONTENT_REPO_PATH=/app/kb-content
KB_CONTENT_REPO_URL=
KB_CONTENT_SSH_KEY_PATH=
KB_CONTENT_DEFAULT_BRANCH=main

# Moodle
MOODLE_DB_USER=moodle
MOODLE_DB_PASSWORD=YOUR_MOODLE_DB_PASSWORD
MOODLE_DB_NAME=moodle
MOODLE_ADMIN_USER=admin
MOODLE_ADMIN_PASSWORD=YOUR_MOODLE_ADMIN_PASSWORD
MOODLE_ADMIN_EMAIL=admin@example.com
MOODLE_SITE_NAME="AI Curator Demo LMS"
```

### 2.3. Замена доменов в `docker-compose.yml`

В production нужно заменить домены в `docker-compose.yml` на ваши. Найдите все строки с `alex-n8n.site` и замените на ваш домен. Например:

```yaml
# было
MOODLE_WWWROOT: https://lms.alex-n8n.site
- "traefik.http.routers.ai-curator-lms.rule=Host(`lms.alex-n8n.site`)"

# стало
MOODLE_WWWROOT: https://lms.example.com
- "traefik.http.routers.ai-curator-lms.rule=Host(`lms.example.com`)"
```

Аналогично замените домены для backend, web-ui и admin-console.

### 2.4. Запуск

```bash
docker compose up --build -d
```

### 2.5. Проверка production-развёртывания

```bash
# Health backend
curl -s https://ai-curator-api.example.com/health
# Expected: {"status":"ok","service":"ai-curator-backend"}

# Проверьте, что все сервисы Up и healthy
docker compose ps
```

---

## Первоначальная настройка после развёртывания

### Создание LMS API-токена

1. Откройте Moodle по адресу `http://localhost:8080` (локально) или `https://lms.example.com` (production).
2. Войдите как администратор.
3. Перейдите: **Администрирование сайта → Сервер → Web services → Управление токенами**.
4. Создайте токен для пользователя, зачисленного в курсы, которые должен обслуживать AI Curator.
5. Запишите токен в `.env` как `LMS_API_TOKEN` и перезапустите backend:

```bash
docker compose up -d ai-curator-backend
```

### Подготовка курса в Moodle

1. Создайте курс с модулями и заданиями.
2. Установите дедлайны заданий.
3. Зачислите студентов.

### Заполнение Базы знаний

1. Откройте Консоль администратора.
2. Войдите с `ADMIN_CONSOLE_TOKEN`.
3. Перейдите в **База знаний → Документы**.
4. Загрузите учебные материалы (Markdown, TXT, PDF).
5. Заполните метаданные: название, тип, course_id, module_id, topic_id, сложность, язык.
6. Нажмите **Переиндексировать**.
7. После успешной индексации опубликуйте документ.

Без опубликованных документов Базы знаний учебные вопросы будут возвращать отказ.

### Demo-режим

Для публичного demo-входа в веб-интерфейсе убедитесь, что `DEMO_ENABLED=true`. Пользователь получает квоту запросов, rate limit и таймер сессии.

---

## Важные замечания

### Безопасность

- `.env` содержит секреты. Не коммитьте его.
- `ADMIN_CONSOLE_TOKEN` и `ADMIN_CONSOLE_DEMO_TOKEN` должны быть длинными случайными строками.
- Используйте read-only Moodle Web Service token.
- Для production настройте firewall: откройте только 80, 443 и SSH.

### Chroma

Chroma 0.5.x хранит SQLite-базу в `/data` внутри контейнера. Volume смонтирован именно туда. Не используйте `latest` для Chroma — образ зафиксирован в `docker-compose.yml`.

### Персистентность данных

Для production убедитесь, что volumes PostgreSQL, Chroma и `kb-content` сохраняются на хосте. По умолчанию Docker Compose создаёт named volumes.

### Traefik и SSL

Перед выпуском сертификатов убедитесь, что DNS-записи разрешаются на сервер. Let's Encrypt имеет rate limits.

---

## Устранение неполадок

| Симптом | Причина | Решение |
|---|---|---|
| `ai-curator-chroma` unhealthy | Отсутствует утилита healthcheck или неверный mount | Проверьте `docker-compose.yml`. Убедитесь, что используется закоммиченная версия. |
| Backend не видит LMS | Неверный `LMS_API_TOKEN` или недостаточно прав | Пересоздайте токен в Moodle с правами чтения курсов, заданий, прогресса. |
| 401 в Консоли администратора | Несовпадение `ADMIN_CONSOLE_TOKEN` | Проверьте `.env` и перезапустите backend. |
| Учебные вопросы возвращают отказ | Документы не опубликованы / не проиндексированы | Проверьте статус документов в Консоли администратора. |
| Директория архивов растёт | Архивы не удаляются с диска | Настройте `logrotate` или cron для очистки `/app/storage/archives` на хосте. |
| SSL-сертификат не выпускается | DNS ещё не обновился или Traefik не видит сеть | Проверьте DNS, убедитесь, что Traefik в сети `n8n_default`. |

---

## Чек-лист Deployment Validation

Развёртывание считается валидным, если в чистом окружении выполнены все пункты:

- [ ] Репозиторий склонирован, `.env` создан с собственными секретами.
- [ ] Для production: DNS-записи настроены, Traefik и сеть `n8n_default` созданы.
- [ ] `docker compose up --build -d` завершается без ошибок.
- [ ] `docker compose ps` показывает все сервисы `Up` и `healthy`.
- [ ] Health endpoint backend возвращает `{"status":"ok"}`.
- [ ] Moodle открывается по своему URL и доступен вход администратора.
[ ] Создан Moodle Web Service token и записан в `.env`.
- [ ] Backend перезапущен с новым `LMS_API_TOKEN`.
- [ ] В Moodle создан курс с заданиями и дедлайнами.
- [ ] В Консоль администратора выполнен вход с `ADMIN_CONSOLE_TOKEN`.
- [ ] Загружен, проиндексирован и опубликован документ в Базе знаний.
- [ ] Чат в веб-интерфейсе отвечает на организационный вопрос с дедлайном из LMS.
- [ ] Чат отвечает на учебный вопрос с источниками из Базы знаний.
- [ ] Запрос `POST /api/v1/demo/start` возвращает токен (при `DEMO_ENABLED=true`).
- [ ] Demo-чат с заголовком `X-Demo-Token` возвращает `demo_mode: true`.
- [ ] После загрузки KB-документа в `kb-content` появляется новый Git-коммит.
