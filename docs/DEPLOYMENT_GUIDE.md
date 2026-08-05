# 🚀 AI Curator — Руководство по развёртыванию

## 🎯 Назначение

Единый Source of Truth для воспроизведения работоспособного экземпляра AI Curator в чистом окружении. Если после выполнения руководства система не работает, руководство устарело.

Руководство рассчитано на технически подготовленного пользователя, знакомого с Docker, Linux и базовой работой DNS.

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта, live demo и обзор.
- [🎛️ `docs/ADMIN_GUIDE.md`](ADMIN_GUIDE.md) — руководство по ежедневной эксплуатации Консоли администратора.
- [📖 `docs/USER_GUIDE.md`](USER_GUIDE.md) — руководство студента по работе с Web UI.
- [🧠 `docs/CURATOR_GUIDE.md`](CURATOR_GUIDE.md) — руководство методиста по наполнению Базы знаний.
- [⚙️ `docs/OPERATIONS.md`](OPERATIONS.md) — эксплуатация, retention, KB workflow.

## 🛠️ Варианты развёртывания

| Вариант | Когда использовать | Публичные домены | Требования |
|---|---|---|---|
| **Локальный запуск** | Первое знакомство, разработка, локальное тестирование | Не нужны | Docker + Docker Compose |
| **Production на VPS** | Публичный demo, пилот, production | Нужны 4 домена | VPS, DNS, Traefik, SSL |

> **Важно:** все примеры доменов, токенов и паролей в этом документе — плейсхолдеры. Никогда не используйте значения из примеров в production.
>
> Все боевые домены заменены на `example.com`. Перед запуском замените домены в `.env` **и** в переменных `LMS_HOST`, `BACKEND_HOST`, `WEB_UI_HOST`, `ADMIN_CONSOLE_HOST`, если они используются для Traefik-правил в `docker-compose.yml`.

---

## 📋 Общие требования

- Linux, macOS или Windows с WSL2.
- Установленные Docker Engine и Docker Compose plugin.
- Клонированный репозиторий:

```bash
git clone https://github.com/AlexLvGulyaev/AI-Curator.git
cd AI-Curator
```

---

## ▶️ Вариант 1. Локальный запуск

Локальный запуск не требует публичных доменов, DNS и Traefik. Сервисы доступны по портам на `localhost`.

### 🔧 1.1. Подготовка `.env`

Создайте файл `.env` в корне репозитория:

```bash
# Backend
APP_ENV=production
DEBUG=false
SECRET_KEY=YOUR_SECRET_KEY
AIC_DB_USER=ai_curator
AIC_DB_PASSWORD=YOUR_AIC_DB_PASSWORD
AIC_DB_NAME=ai_curator
DATABASE_URL=postgresql+asyncpg://ai_curator:YOUR_AIC_DB_PASSWORD@ai-curator-postgres:5432/ai_curator
TEST_DATABASE_URL=postgresql+asyncpg://ai_curator:YOUR_AIC_DB_PASSWORD@ai-curator-postgres:5432/ai_curator_test
PYTEST_ALLOW_PROD_DB=false
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# Fallback chat model. Active model is configured in Admin Console → AI & Retrieval.
OPENAI_MODEL=gpt-4o-mini

# Optional fallback provider: GigaChat (Sber)
# GIGACHAT_AUTH_KEY=YOUR_GIGACHAT_AUTHORIZATION_KEY
# GIGACHAT_BASE_URL=https://gigachat.devices.sberbank.ru/api/v1
# GIGACHAT_TOKEN_URL=https://ngw.devices.sberbank.ru:9443/api/v2/oauth
# GIGACHAT_MODEL=GigaChat-Max

CHROMA_HOST=ai-curator-chroma
CHROMA_PORT=8000
CHROMA_COLLECTION_NAME=ai_curator_kb
CHROMA_TEST_COLLECTION_NAME=ai_curator_kb_test
CACHE_FILE_PATH=/app/storage/cache/response_cache.json
CACHE_TTL_SECONDS=86400
DOC_STORE_PATH=/app/storage/documents

# LMS integration (use service name inside Docker network, not localhost)
LMS_BASE_URL=http://ai-curator-lms
LMS_HOST=lms.example.com
LMS_API_TOKEN=YOUR_MOODLE_WEBSERVICE_TOKEN

# Admin Console auth
ADMIN_CONSOLE_URL=http://localhost:3001
ADMIN_CONSOLE_HOST=ai-curator-admin.example.com
ADMIN_CONSOLE_TOKEN=YOUR_RANDOM_HEX_TOKEN_64_CHARS
ADMIN_CONSOLE_DEMO_TOKEN=YOUR_DEMO_READONLY_TOKEN_64_CHARS

# Web UI
WEB_UI_URL=http://localhost:3000
BACKEND_API_URL=http://localhost:8000
WEB_UI_HOST=ai-curator.example.com
BACKEND_HOST=ai-curator-api.example.com

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
MOODLE_VERSION=MOODLE_404_STABLE
```

### 🔧 1.2. Создание `docker-compose.override.yml`

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

### 🌐 1.3. Подготовка Docker-сети

Локальный стек использует ту же внешнюю сеть `n8n_default`, что и production-вариант. Создайте её перед первым запуском:

```bash
docker network create n8n_default
```

### ▶️ 1.4. Запуск

```bash
docker compose up --build -d
```

### ✅ 1.5. Проверка локального развёртывания

```bash
# Health backend
curl -s http://localhost:8000/health
# Expected: {"status":"ok","service":"ai-curator-backend"}

# Moodle доступен на http://localhost:8080
# Web UI на http://localhost:3000
# Admin Console на http://localhost:3001
```

---

## ▶️ Вариант 2. Production на VPS

### 🧰 2.1. Подготовка инфраструктуры

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

### 🔧 2.2. Подготовка `.env`

Замените `example.com` на ваши реальные домены и заполните секреты:

```bash
# Backend
APP_ENV=production
DEBUG=false
SECRET_KEY=YOUR_SECRET_KEY
AIC_DB_USER=ai_curator
AIC_DB_PASSWORD=YOUR_AIC_DB_PASSWORD
AIC_DB_NAME=ai_curator
DATABASE_URL=postgresql+asyncpg://ai_curator:YOUR_AIC_DB_PASSWORD@ai-curator-postgres:5432/ai_curator
TEST_DATABASE_URL=postgresql+asyncpg://ai_curator:YOUR_AIC_DB_PASSWORD@ai-curator-postgres:5432/ai_curator_test
PYTEST_ALLOW_PROD_DB=false
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
# Fallback chat model. Active model is configured in Admin Console → AI & Retrieval.
OPENAI_MODEL=gpt-4o-mini

# Optional fallback provider: GigaChat (Sber)
# GIGACHAT_AUTH_KEY=YOUR_GIGACHAT_AUTHORIZATION_KEY
# GIGACHAT_BASE_URL=https://gigachat.devices.sberbank.ru/api/v1
# GIGACHAT_TOKEN_URL=https://ngw.devices.sberbank.ru:9443/api/v2/oauth
# GIGACHAT_MODEL=GigaChat-Max

CHROMA_HOST=ai-curator-chroma
CHROMA_PORT=8000
CHROMA_COLLECTION_NAME=ai_curator_kb
CHROMA_TEST_COLLECTION_NAME=ai_curator_kb_test
CACHE_FILE_PATH=/app/storage/cache/response_cache.json
CACHE_TTL_SECONDS=86400
DOC_STORE_PATH=/app/storage/documents

# LMS integration
LMS_BASE_URL=https://lms.example.com
LMS_API_TOKEN=YOUR_MOODLE_WEBSERVICE_TOKEN

# Admin Console auth
ADMIN_CONSOLE_URL=https://ai-curator-admin.example.com
ADMIN_CONSOLE_TOKEN=YOUR_RANDOM_HEX_TOKEN_64_CHARS
ADMIN_CONSOLE_DEMO_TOKEN=YOUR_DEMO_READONLY_TOKEN_64_CHARS

# Web UI
WEB_UI_URL=https://ai-curator.example.com
BACKEND_API_URL=https://ai-curator-api.example.com
WEB_UI_HOST=ai-curator.example.com
BACKEND_HOST=ai-curator-api.example.com

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
MOODLE_VERSION=MOODLE_404_STABLE
```

### 🌐 2.3. Замена доменов

В `docker-compose.yml` домены Traefik-правил и `VITE_API_BASE_URL` уже параметризованы через переменные окружения. Замените домены в `.env`:

```bash
LMS_BASE_URL=https://lms.yourdomain.com
LMS_HOST=lms.yourdomain.com

WEB_UI_URL=https://ai-curator.yourdomain.com
WEB_UI_HOST=ai-curator.yourdomain.com

BACKEND_API_URL=https://ai-curator-api.yourdomain.com
BACKEND_HOST=ai-curator-api.yourdomain.com

ADMIN_CONSOLE_URL=https://ai-curator-admin.yourdomain.com
ADMIN_CONSOLE_HOST=ai-curator-admin.yourdomain.com
```

Переменные `*_HOST` используются в labels Traefik-роутеров, а `*_URL` — внутри приложений и для `MOODLE_WWWROOT`.

### ▶️ 2.4. Запуск

```bash
docker compose up --build -d
```

### ✅ 2.5. Проверка production-развёртывания

```bash
# Health backend
curl -s https://ai-curator-api.example.com/health
# Expected: {"status":"ok","service":"ai-curator-backend"}

# Проверьте, что все сервисы Up и healthy
docker compose ps
```

---

## 🔧 Первоначальная настройка после развёртывания

### 🔌 Включение Moodle Web Services

1. Откройте Moodle по адресу `http://localhost:8080` (локально) или `https://lms.example.com` (production).
2. Войдите как администратор.
3. Перейдите: **Администрирование сайта → Сервер → Web services → Обзор**.
4. Включите внешние службы: переведите переключатель **Включить веб-службы** в положение **Да**.
5. Перейдите в **Управление протоколами** и включите протокол **REST**.
6. Перейдите в **Управление службами**, создайте службу (например, `ai_curator_service`) и добавьте в неё функции:
   - `core_course_get_courses`
   - `core_course_get_contents`
   - `mod_assign_get_assignments`
   - `core_completion_get_activities_completion_status`
   - `core_user_get_users_by_field` (если нужно разрешать пользователей)
7. Включите службу и разрешите её для авторизованных пользователей.

### 🔑 Создание LMS API-токена

1. Перейдите: **Администрирование сайта → Сервер → Web services → Управление токенами**.
2. Создайте токен для пользователя, зачисленного в курсы, которые должен обслуживать AI Curator, и привяжите его к службе `ai_curator_service`.
3. Запишите токен в `.env` как `LMS_API_TOKEN` и перезапустите backend:

```bash
docker compose up -d ai-curator-backend
```

### 📚 Подготовка курса в Moodle

1. Создайте курс с модулями и заданиями.
2. Установите дедлайны заданий.
3. Зачислите студентов.

### 📚 Заполнение Базы знаний

1. Откройте Консоль администратора.
2. Войдите с `ADMIN_CONSOLE_TOKEN`.
3. Перейдите в **База знаний → Документы**.
4. Загрузите учебные материалы (Markdown, TXT, PDF).
5. Заполните метаданные: название, тип, course_id, module_id, topic_id, сложность, язык.
6. Нажмите **Переиндексировать**.
7. После успешной индексации опубликуйте документ.

Без опубликованных документов Базы знаний учебные вопросы будут возвращать отказ.

### 🔓 Demo-режим

Для публичного demo-входа в веб-интерфейсе убедитесь, что `DEMO_ENABLED=true`. Пользователь получает квоту запросов, rate limit и таймер сессии.

> **Примечание:** `DEMO_ENABLED=true` позволяет открывать Web UI без аутентификации студента. Для закрытого портала, где вход должен происходить только через LMS/SSO, установите `DEMO_ENABLED=false`.

---

## 🛡️ Важные замечания

### 🛡️ Безопасность

- `.env` содержит секреты. Не коммитьте его.
- `ADMIN_CONSOLE_TOKEN` и `ADMIN_CONSOLE_DEMO_TOKEN` должны быть длинными случайными строками.
- Используйте read-only Moodle Web Service token.
- Для production настройте firewall: откройте только 80, 443 и SSH.

### 🗄️ Chroma

Chroma 0.5.x хранит SQLite-базу в `/data` внутри контейнера. Volume смонтирован именно туда. Не используйте `latest` для Chroma — образ зафиксирован в `docker-compose.yml`.

### 💾 Персистентность данных

Для production убедитесь, что volumes PostgreSQL, Chroma и `kb-content` сохраняются на хосте. По умолчанию Docker Compose создаёт named volumes.

### 🔒 Traefik и SSL

Перед выпуском сертификатов убедитесь, что DNS-записи разрешаются на сервер. Let's Encrypt имеет rate limits.

---

## 🛠️ Устранение неполадок

| Симптом | Причина | Решение |
|---|---|---|
| `ai-curator-chroma` unhealthy | Отсутствует утилита healthcheck или неверный mount | Проверьте `docker-compose.yml`. Убедитесь, что используется закоммиченная версия. |
| Backend не видит LMS | Неверный `LMS_API_TOKEN` или недостаточно прав | Пересоздайте токен в Moodle с правами чтения курсов, заданий, прогресса. |
| 401 в Консоли администратора | Несовпадение `ADMIN_CONSOLE_TOKEN` | Проверьте `.env` и перезапустите backend. |
| Учебные вопросы возвращают отказ | Документы не опубликованы / не проиндексированы | Проверьте статус документов в Консоли администратора. |
| Директория архивов растёт | Архивы не удаляются с диска | Настройте `logrotate` или cron для очистки `/app/storage/archives` на хосте. |
| SSL-сертификат не выпускается | DNS ещё не обновился или Traefik не видит сеть | Проверьте DNS, убедитесь, что Traefik в сети `n8n_default`. |

---

## 📝 История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-08-05 | 1.1 | Параметризация БД (`AIC_DB_*`), замена боевых доменов на placeholder-переменные (`*_HOST`, `*_URL`), исправлен `OPENAI_CHAT_MODEL` → `OPENAI_MODEL`, исправлен локальный `LMS_BASE_URL`, добавлена подготовка `n8n_default`, расширены `.env` примеры, добавлена настройка Moodle Web Services |
| 2026-08-05 | 1.0 | Актуализация под Sprint F: demo mode, log retention, KB Content Git, CSV export |

---

## ✅ Чек-лист Deployment Validation

Развёртывание считается валидным, если в чистом окружении выполнены все пункты:

- [ ] Репозиторий склонирован, `.env` создан с собственными секретами.
- [ ] Для production: DNS-записи настроены, Traefik и сеть `n8n_default` созданы.
- [ ] `docker compose up --build -d` завершается без ошибок.
- [ ] `docker compose ps` показывает все сервисы `Up` и `healthy`.
- [ ] Health endpoint backend возвращает `{"status":"ok"}`.
- [ ] Moodle открывается по своему URL и доступен вход администратора.
- [ ] Создан Moodle Web Service token и записан в `.env`.
- [ ] Backend перезапущен с новым `LMS_API_TOKEN`.
- [ ] В Moodle создан курс с заданиями и дедлайнами.
- [ ] В Консоль администратора выполнен вход с `ADMIN_CONSOLE_TOKEN`.
- [ ] Загружен, проиндексирован и опубликован документ в Базе знаний.
- [ ] Чат в веб-интерфейсе отвечает на организационный вопрос с дедлайном из LMS.
- [ ] Чат отвечает на учебный вопрос с источниками из Базы знаний.
- [ ] Запрос `POST /api/v1/demo/start` возвращает токен (при `DEMO_ENABLED=true`).
- [ ] Demo-чат с заголовком `X-Demo-Token` возвращает `demo_mode: true`.
- [ ] После загрузки KB-документа в `kb-content` появляется новый Git-коммит.
