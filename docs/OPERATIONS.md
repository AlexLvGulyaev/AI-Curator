# OPERATIONS.md — AI Curator

**Проект:** ai-curator  
**Версия:** 1.0  
**Дата:** 2026-07-30  
**Статус:** Актуален для Дня 6

---

## 1. Назначение

Руководство по эксплуатации AI Curator: обновление Knowledge Base, управление AI-конфигурацией, просмотр аналитики и мониторинга.

---

## 2. Knowledge Base

### 2.1. Добавление нового материала

1. Откройте Admin Console: `https://curator-admin.alex-n8n.site`.
2. Войдите с Bearer-токеном (`ADMIN_CONSOLE_TOKEN`).
3. Перейдите в раздел **Knowledge Base** → **Загрузить документ**.
4. Укажите название, тип документа, курс/модуль/тему, сложность, язык, описание и файл.
5. Нажмите **Сохранить документ**.
6. В списке документов нажмите **Обработать** для chunking, embeddings и индексации в Chroma.
7. После успешной обработки нажмите **Опубликовать**.

### 2.2. Обновление версии документа

1. Откройте карточку документа.
2. В разделе **Версии** выберите новый файл и нажмите **Загрузить версию**.
3. Новая версия становится активной, старая версия исключается из индекса.
4. Нажмите **Обработать** для переиндексации.

### 2.3. Снятие материала с публикации

1. В списке документов найдите нужный.
2. Нажмите **Снять** в колонке «Публикация».
3. Документ остаётся в хранилище, но не участвует в retrieval.

### 2.4. Удаление документа

1. В списке документов нажмите **Удалить**.
2. Подтвердите действие.
3. Документ и все версии мягко удаляются (status = `archived`).

### 2.5. Git workflow для материалов KB

Каждый загруженный или отредактированный файл материала сохраняется в отдельном Git-репозитории `kb-content/`. Это даёт:

- версионирование исходников;
- восстановление предыдущих редакций;
- заполнение Git-метаданных версии документа (`git_commit_hash`, `git_blob_hash`).

#### Режимы работы

| Режим | `KB_CONTENT_REPO_URL` | `KB_CONTENT_GIT_ENABLED` | Поведение |
|-------|----------------------|--------------------------|-----------|
| Локальный (dev) | пусто | `true` | Backend делает локальные commit'ы в `./kb-content/`, push не выполняется. |
| Remote (production) | `git@github.com:org/kb-content.git` | `true` | Клон/clone remote, pull перед commit, push после commit. |
| Отключён | любое | `false` | Файлы сохраняются в `DOC_STORE_PATH`, Git-метаданные не заполняются. |

#### Проверить Git-метаданные версии

В Admin Console → Knowledge Base → Документы откройте карточку документа. В разделе **ПАСПОРТ** / **ЭКСПЛУАТАЦИЯ** должны отображаться:

- `git_commit_hash` — хеш последнего commit'а, в котором участвовал файл;
- `git_blob_hash` — хеш blob'а файла в HEAD;
- `git_author` — автор commit'а (по умолчанию `AI Curator`).

Если поля пустые после загрузки:

1. Проверьте `KB_CONTENT_GIT_ENABLED=true` и `KB_CONTENT_REPO_PATH=/app/kb-content` в `.env`.
2. Убедитесь, что в `docker-compose.yml` есть bind-mount `./kb-content:/app/kb-content` для `ai-curator-backend`.
3. Перезапустите backend-контейнер.
4. Перезагрузите файл — при успешном commit'е метаданные появятся.

#### Редактирование cleaned-текста

1. В карточке документа переключите **PREVIEW ТЕКСТА** в режим **ОЧИЩЕННЫЙ**.
2. Нажмите **Открыть**.
3. Отредактируйте текст в модальном редакторе.
4. Нажмите **Сохранить и переиндексировать**.
5. Backend сохранит новый cleaned-текст в `kb-content/`, сделает commit, обновит `sha256` и пересчитает чанки.

---

## 3. AI Configuration

### 3.1. Просмотр активной конфигурации

Раздел **AI Configuration** показывает активную версию: модель, temperature, max_tokens, top_k_retrieval, rag_distance_threshold, system_prompt, beginner/advanced instructions, few-shot examples, output rules, refusal answer text, max_history_messages.

### 3.2. Создание новой версии

1. Введите название версии.
2. Отредактируйте `system_prompt`, модель, температуру, лимит токенов и параметры retrieval (`top_k_retrieval`, `rag_distance_threshold`).
3. При необходимости измените тексты для beginner/advanced уровня, few-shot примеры, output rules и текст стандартного отказа.
4. Нажмите **Создать новую версию**.

### 3.3. Активация версии

В таблице **История версий** нажмите **Активировать** у нужной строки. Все остальные версии становятся неактивными.

---

## 4. Аналитика

Раздел **Аналитика** содержит:

- ключевые метрики: количество запросов, ответов, средняя задержка, вопросы без ответа;
- распределение запросов по темам (намерениям);
- распределение оценок полезности;
- список вопросов без ответа.

Аналитика читается из PostgreSQL: таблицы `chat_requests`, `chat_logs`, `analytics_events`.

### 4.1. Мониторинг latency

Каждый chat-ответ записывает полную разбивку latency в `analytics_events.payload.timings_ms`:

| Метрика | Компонент | Целевое значение |
|---------|-----------|------------------|
| `intent_detect_ms` | Классификация | < 10 мс |
| `lms_deadlines_ms` / `lms_progress_ms` / `lms_contents_ms` | LMS Adapter | параллельно, сумма не критична; каждый < 3 сек |
| `rag_embedding_ms` | RAG embedding (кэш или OpenAI) | < 1000 мс холодный, < 10 мс из кэша |
| `rag_chroma_ms` | Chroma query | < 500 мс |
| `rag_postprocess_ms` | Фильтрация + дедупликация | < 50 мс |
| `llm_generate_ms` | LLM generation | < 4000 мс (зависит от `max_tokens`) |
| `validation_ms` | Answer Validator | < 200 мс |

Общая latency отчитывается в `chat_logs.latency_ms` и в ответе API как `latency_ms`.

### 4.2. Профилирование вручную

Для замера latency на живом backend выполните изнутри контейнера:

```bash
docker exec ai-curator-backend python /app/scripts/profile_latency.py
```

Скрипт делает 5 вызовов по 6 сценариям (30 запросов) и выводит p50/mean/max.

### 4.3. SLO и NFR

- **NFR-1:** p50 latency на типовых chat-сценариях ≤ **5 секунд**.
- **SLO:** p95 ≤ 8 сек для холодного старта.
- **Профилирование Sprint 4 (2026-07-30):** все сценарии уложились в 5 сек; максимальный measured latency — 3547 мс (`study_basic`, холодный старт).

---

## 5. Мониторинг

Раздел **Панель состояния** отображает статус:

- базы данных PostgreSQL;
- LMS-интеграции;
- Chroma (векторного индекса);
- LLM Provider (наличие ключа OpenAI).

Также доступны JSON endpoints:

- `GET /api/v1/admin/monitoring/status`
- `GET /api/v1/admin/monitoring/health`

---

## 6. Аудит

Административные действия фиксируются в таблице `audit_logs`. Просмотр доступен в разделе **Журнал аудита**.

---

## 7. Переменные окружения

| Переменная | Описание |
|------------|----------|
| `ADMIN_CONSOLE_TOKEN` | Bearer-токен для доступа к Admin Console |
| `OPENAI_API_KEY` | Ключ OpenAI API |
| `LMS_API_TOKEN` | Токен Moodle API |
| `DATABASE_URL` | URL подключения к PostgreSQL |
| `CHROMA_HOST` / `CHROMA_PORT` | Подключение к Chroma |
| `WEB_UI_URL` / `ADMIN_CONSOLE_URL` | Публичные URL для CORS |
| `ARCHIVE_DIR` | Путь к локальному архиву логов (по умолчанию `./storage/archives`) |
| `HOT_RETENTION_DAYS` | Срок хранения логов в PostgreSQL (по умолчанию 30) |
| `TRACE_RETENTION_DAYS` | Срок хранения полных prompt/response traces (по умолчанию 7) |
| `OPENAI_MODEL_MAX_TOKENS` | Fallback max output tokens для LLM (по умолчанию 1024) |
| `KB_CONTENT_GIT_ENABLED` | Включить Git workflow для материалов KB (`true`/`false`) |
| `KB_CONTENT_REPO_URL` | SSH URL удалённого Git-репозитория (`git@github.com:...`). Пусто = локальный режим. |
| `KB_CONTENT_REPO_PATH` | Путь к рабочей копии внутри контейнера (по умолчанию `/app/kb-content`) |
| `KB_CONTENT_SSH_KEY_PATH` | Путь к SSH-ключу для push в remote (внутри контейнера) |
| `KB_CONTENT_DEFAULT_BRANCH` | Ветка по умолчанию (`main`) |

### AI Config tuning для latency

В Admin Console можно влиять на latency через параметры активной конфигурации:

| Параметр | Влияние на latency | Рекомендация |
|----------|-------------------|--------------|
| `max_tokens` | Жёсткий потолок длины ответа LLM | 512–1024 для chat; выше — медленнее |
| `top_k_retrieval` | Сколько RAG-чанков попадает в prompt | Для chat переопределяется кодом до 3; для Admin оставить 5 |
| `rag_distance_threshold` | Фильтр шумных чанков | 1.35 по умолчанию; уменьшение ускоряет, но может снизить recall |
| `system_prompt` + `output_rules` | Размер prompt | Избыточный текст увеличивает prompt tokens и latency |
| `max_history_messages` | Длина истории в prompt | Меньше сообщений — меньше токенов |

### AI Config — default instructions backfill

Backend автоматически подставляет дефолтные значения в `beginner_instructions` и `advanced_instructions`, если активная конфигурация не содержит этих полей (`NULL` или пустая строка). Это защищает от ситуации, когда учебный вопрос для beginner получает отказ из-за отсутствия чёткой инструкции отвечать на основе контекста.

Рекомендуемое содержание `beginner_instructions`:

```text
Уровень подготовки: beginner. Объясняй просто и с примерами, но обязательно на основе предоставленных материалов. Если в контексте есть релевантная информация — ответь кратко, даже если она неполная. Не отказывайся от ответа, когда дан предоставленный контекст.
```

Проверить текущие инструкции активной конфигурации:

```bash
docker exec ai-curator-backend python3 -c "
import asyncio
from db import async_session_factory
from services.ai_config import AiConfigService
async def main():
    async with async_session_factory() as db:
        cfg = await AiConfigService(db).get_active()
        print('beginner:', cfg.beginner_instructions)
        print('advanced:', cfg.advanced_instructions)
asyncio.run(main())
"
```

---

## 8. Retention и архивы

Старые логи автоматически архивируются и удаляются из PostgreSQL фоновым процессом Backend.

Проверить последний cleanup:

```bash
docker exec ai-curator-backend ls -la /app/storage/archives/
```

Вручную запустить cleanup (для отладки):

```bash
docker exec ai-curator-backend python3 -c "
import asyncio
from db import async_session_factory
from services.logger import LoggerService
async def main():
    async with async_session_factory() as db:
        logger = LoggerService(db)
        deleted = await logger.cleanup_old_records('/app/storage/archives')
        print(deleted)
asyncio.run(main())
"
```

## 9. История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-07-30 | 1.0 | Создан документ |
 | 2026-07-30 | 1.1 | Добавлены расширенные параметры AI Config, retention и архивирование логов |
| 2026-07-30 | 1.2 | Добавлен раздел мониторинга latency: метрики из `analytics_events`, ручное профилирование через `scripts/profile_latency.py`, SLO/NFR, AI Config tuning для latency |
| 2026-07-30 | 1.3 | Добавлен раздел AI Config default instructions backfill; задокументировано устранение критичного дефекта beginner-ответов в Sprint 4 |
| 2026-07-31 | 1.4 | Добавлен раздел 2.5 «Git workflow для материалов KB» и переменные окружения KB Content Git |
