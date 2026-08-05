# AI Curator — Руководство по развёртыванию

## Назначение

Этот документ — единый Source of Truth для воспроизведения полностью работоспособного экземпляра AI Curator. Следуйте инструкциям по порядку; если после выполнения система не работает, документ устарел.

## Требования

- Сервер на Linux с установленными Docker Engine и плагином Docker Compose.
- Публичные DNS-записи, направленные на сервер (для production с Traefik):
  - `curator.alex-n8n.site` → Веб-интерфейс
  - `curator-admin.alex-n8n.site` → Консоль администратора
  - `curator-api.alex-n8n.site` → Backend API
  - `lms.alex-n8n.site` → Moodle LMS
- Обратный прокси Traefik в Docker-сети `n8n_default` (только для production). Для локального развёртывания сервисы используют внутренние порты.

## Обязательные переменные окружения

Создайте `.env` в корне репозитория как минимум со следующими переменными:

```bash
# Backend
DATABASE_URL=postgresql+asyncpg://ai_curator:AICPG3hfpf2100@ai-curator-postgres:5432/ai_curator
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini-2024-07-18
CHROMA_HOST=ai-curator-chroma
CHROMA_PORT=8000

# Интеграция с LMS
LMS_BASE_URL=https://lms.alex-n8n.site
LMS_API_TOKEN=YOUR_MOODLE_WEBSERVICE_TOKEN

# Аутентификация в Консоли администратора
ADMIN_CONSOLE_URL=https://curator-admin.alex-n8n.site
ADMIN_CONSOLE_TOKEN=YOUR_RANDOM_HEX_TOKEN_64_CHARS
# Опционально: отдельный read-only demo-токен для Консоли администратора.
ADMIN_CONSOLE_DEMO_TOKEN=YOUR_DEMO_READONLY_TOKEN_64_CHARS

# Веб-интерфейс
WEB_UI_URL=https://curator.alex-n8n.site

# Безопасный demo-режим веб-интерфейса (Sprint F)
# В production установите DEMO_ENABLED=true, чтобы публичный чат требовал X-Demo-Token.
DEMO_ENABLED=false
DEMO_MAX_REQUESTS_PER_SESSION=20
DEMO_SESSION_TTL_MINUTES=30
DEMO_RATE_LIMIT_PER_MINUTE=12
DEMO_MAX_SESSIONS_PER_IP_PER_HOUR=5
DEMO_CACHE_TTL_SECONDS=604800

# Ротация и архивирование логов
ARCHIVE_DIR=/app/storage/archives
HOT_RETENTION_DAYS=30
TRACE_RETENTION_DAYS=7

# Горячие логи (chat_requests, chat_logs, analytics_events, audit_logs, llm_calls)
# архивируются после HOT_RETENTION_DAYS и удаляются из PostgreSQL.
# Полные трейсы LLM-вызовов (llm_call_traces) архивируются после TRACE_RETENTION_DAYS.
# Очистка запускается раз в сутки; архивы — gzip-сжатые JSON Lines в ARCHIVE_DIR.

# Git-репозиторий контента Базы знаний
KB_CONTENT_GIT_ENABLED=true
KB_CONTENT_REPO_PATH=/app/kb-content
# Оставьте пустым для локального режима или укажите SSH-URL для production-синхронизации:
KB_CONTENT_REPO_URL=
KB_CONTENT_SSH_KEY_PATH=
KB_CONTENT_DEFAULT_BRANCH=main

# Moodle (только если используется встроенный LMS-стек)
MOODLE_DB_USER=moodle
MOODLE_DB_PASSWORD=YOUR_MOODLE_DB_PASSWORD
MOODLE_DB_NAME=moodle
MOODLE_ADMIN_USER=admin
MOODLE_ADMIN_PASSWORD=YOUR_MOODLE_ADMIN_PASSWORD
MOODLE_ADMIN_EMAIL=admin@example.com
MOODLE_SITE_NAME=AI Curator Demo LMS
```

Никогда не коммитьте `.env` в репозиторий. Он уже добавлен в `.gitignore`.

## Сборка и запуск

Из корня репозитория:

```bash
docker compose up --build -d
```

Команда собирает образы backend, веб-интерфейса, консоли администратора и запускает:
- PostgreSQL для backend (`ai-curator-postgres`)
- Векторное хранилище Chroma (`ai-curator-chroma`)
- Moodle LMS + его PostgreSQL (`ai-curator-lms`, `ai-curator-lms-db`)
- Backend API (`ai-curator-backend`)
- Веб-интерфейс (`ai-curator-web-ui`)
- Консоль администратора (`ai-curator-admin-console`)

## Проверка развёртывания

Дождитесь, пока все контейнеры перейдут в статус `healthy`:

```bash
docker compose ps
```

Проверьте health backend:

```bash
curl -s https://curator-api.alex-n8n.site/health
```

Ожидаемый результат: `{"status":"ok","service":"ai-curator-backend"}`.

### Проверка экспорта логов и ротации

Запустите экспорт операционных логов:

```bash
curl -s -X POST "https://curator-api.alex-n8n.site/api/v1/admin/operational-logs/export?date_from=2026-08-01" \
  -H "Authorization: Bearer $ADMIN_CONSOLE_TOKEN" \
  -o /tmp/ai_curator_operational_logs.csv

head /tmp/ai_curator_operational_logs.csv
```

Ожидаемый результат: CSV-файл с заголовками `id,session_id,role,course_id,...`.

Проверьте директорию архивов:

```bash
docker exec ai-curator-backend ls -la /app/storage/archives/
```

Ожидаемый результат: директория существует; после первой очистки (в течение 24 часов после запуска) в ней появятся gzip-архивы для таблиц старше срока retention.

### Проверка безопасного demo-режима (при `DEMO_ENABLED=true`)

Создайте demo-сессию:

```bash
curl -s -X POST https://curator-api.alex-n8n.site/api/v1/demo/start \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Ожидаемый результат: JSON-объект с полями `token`, `requests_limit`, `requests_remaining` и `expires_at`.

Используйте токен для чата:

```bash
export DEMO_TOKEN=<token-from-above>
curl -s -X POST https://curator-api.alex-n8n.site/api/v1/chat \
  -H 'Content-Type: application/json' \
  -H "X-Demo-Token: $DEMO_TOKEN" \
  -d '{"message":"Какие дедлайны?","role":"active_student","difficulty":"beginner","course_id":3}'
```

Ожидаемый результат: `200 OK` и `demo_mode: true` в ответе.

Проверьте оставшуюся квоту:

```bash
curl -s https://curator-api.alex-n8n.site/api/v1/demo/status \
  -H "X-Demo-Token: $DEMO_TOKEN"
```

Ожидаемый результат: `requests_used` увеличен, `requests_remaining` уменьшен.

## Первоначальная настройка

### 1. Заполнение Moodle демо-данными (опционально, для E2E-тестирования)

```bash
docker exec ai-curator-backend python3 /app/scripts/seed-lms-demo-data.py
```

Команда создаёт три demo-роли студентов с разными профилями прогресса и пересоздаёт структуру курса «Промпт-инжиниринг».

### 2. Создание LMS API-токена

В Moodle:
1. Site Administration → Server → Web services → Manage tokens.
2. Создайте токен для пользователя, зачисленного или имеющего право управления во всех курсах, которые должен обслуживать чат.
3. Поместите токен в `.env` как `LMS_API_TOKEN` и перезапустите backend.

### 3. Индексация документов Базы знаний

1. Откройте Консоль администратора: `https://curator-admin.alex-n8n.site`.
2. Войдите, используя значение `ADMIN_CONSOLE_TOKEN`.
3. Загрузите учебные материалы в разделе Базы знаний.
4. Опубликуйте документы, чтобы они стали доступны для поиска.

Без опубликованных документов Базы знаний учебные вопросы будут возвращать отказ из-за отсутствия контекста.

### 4. Git-репозиторий контента Базы знаний (опционально, но рекомендуется)

По умолчанию директория `kb-content/` монтируется в backend-контейнер по пути `/app/kb-content` и отслеживается как локальный Git-репозиторий. Backend фиксирует каждый загруженный или отредактированный исходный файл KB и сохраняет `git_commit_hash` / `git_blob_hash` в версии документа.

#### Локальный режим (development / demo)

При `KB_CONTENT_REPO_URL=` (пусто) backend инициализирует локальный репозиторий внутри контейнера и коммитит локально. Ничего не отправляется на удалённый сервер. Рабочая копия сохраняется на хосте Docker через bind mount, поэтому коммиты переживают пересоздание контейнера.

Проверьте локальный репозиторий:

```bash
docker exec ai-curator-backend git -C /app/kb-content log --oneline -3
```

Ожидаемый результат: недавние коммиты от загрузки документов, например:

```text
a1b2c3d feat(kb): upload "CC01. Установка и первый запуск Claude Code"
01f72e9 init(kb-content): course materials for Claude Code training
```

#### Production-режим с удалённым репозиторием

1. Создайте выделенный репозиторий, например `git@github.com:your-org/ai-curator-kb-content.git`.
2. Сгенерируйте SSH deploy key с правами **read/write** и сохраните приватный ключ на сервере, например `/opt/ai-curator-kb-content-deploy.key`.
3. Укажите в `.env`:

```bash
KB_CONTENT_REPO_URL=git@github.com:your-org/ai-curator-kb-content.git
KB_CONTENT_SSH_KEY_PATH=/app/secrets/kb-content-deploy.key
KB_CONTENT_GIT_ENABLED=true
```

4. Смонтируйте deploy key в backend-контейнер, добавив в `docker-compose.yml` в раздел `ai-curator-backend.volumes`:

```yaml
- ./secrets/kb-content-deploy.key:/app/secrets/kb-content-deploy.key:ro
```

5. Убедитесь, что ключ не попал в репозиторий (добавьте `secrets/` в `.gitignore`).
6. Перезапустите backend:

```bash
docker compose up -d ai-curator-backend
```

7. Загрузите или отредактируйте документ в Консоли администратора. Backend выполнит clone/push в удалённый репозиторий и заполнит Git-метаданные версии.

#### Проверка удалённой синхронизации

```bash
docker exec ai-curator-backend git -C /app/kb-content log --oneline --decorate -3
```

Если удалённый репозиторий настроен, на последнем коммите должна быть метка `(origin/main)`.

## Важные замечания по развёртыванию

### Персистентность Chroma

Chroma 0.5.x хранит SQLite-базу в `/data` внутри контейнера. Docker Compose volume смонтирован именно туда. В production **не используйте** `latest` для Chroma — образ зафиксирован конкретным digest в `docker-compose.yml`.

### Доступ к курсам в LMS

Если курс виден студентам, но сервисный токен не может прочитать его задания, backend автоматически переходит к парсингу дедлайнов из `core_course_get_contents`. Это прозрачно для пользователя.

### Traefik

Production-маршрутизация зависит от внешней Docker-сети `n8n_default`. Убедитесь, что Traefik подключён к этой сети и DNS-записи разрешаются на сервер до выпуска сертификатов.

## Перезапуск после изменения кода

```bash
docker compose build ai-curator-backend
docker compose up -d ai-curator-backend
```

## Устранение неполадок

| Симптом | Причина | Решение |
|---------|---------|---------|
| `ai-curator-chroma` unhealthy | Отсутствует утилита healthcheck или неверный mount | Образ и healthcheck зафиксированы в `docker-compose.yml`. Если видите `wget: not found`, обновите до последней закоммиченной версии. |
| Учебные вопросы возвращают отказ после перезапуска | Volume Chroma смонтирован не в `/data`, данные потеряны при пересоздании контейнера | Убедитесь в монтировании `/data`. При необходимости повторно загрузите и проиндексируйте документы. |
| Отсутствуют дедлайны курсов 4+ | У сервисного токена нет capability `mod_assign_get_assignments` | Используйте fallback-поведение или зачислите пользователя токена на курс. |
| Консоль администратора возвращает 401 | Несовпадение `ADMIN_CONSOLE_TOKEN` | Проверьте `.env` и перезапустите backend. |
| `/app/storage/archives` неограниченно растёт | Логи архивируются, но не удаляются с диска | Настройте logrotate или регулярную очистку на Docker-хосте. |

## Чек-лист валидации

После свежего развёртывания проверьте:

- [ ] `docker compose ps` показывает все сервисы `Up` и `healthy`.
- [ ] Health endpoint backend возвращает `{"status":"ok"}`.
- [ ] Запрос-отказ (`Выставь мне зачёт...`) возвращает `intent: refusal` и `latency_ms: 0`.
- [ ] Вопрос про дедлайн возвращает корректную дату из LMS.
- [ ] Учебный вопрос возвращает ответ на основе Базы знаний с источниками.
- [ ] После загрузки документа `docker exec ai-curator-backend git -C /app/kb-content log --oneline -3` показывает новый коммит.
- [ ] Версия загруженного документа в Консоли администратора отображает непустые `git_commit_hash` и `git_blob_hash`.
