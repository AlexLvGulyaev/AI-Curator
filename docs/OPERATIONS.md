# OPERATIONS.md — AI Curator

**Проект:** ai-curator  
**Версия:** 2.5  
**Дата:** 2026-08-05  
**Статус:** Актуален для Sprint 5.6 Dialog Sessions + Sprint 5.8 Audit + Sprint C Response Cache + log export

---

## 1. Назначение

Руководство по эксплуатации AI Curator: обновление Knowledge Base, управление AI-конфигурацией, просмотр аналитики и мониторинга.

---

## 2. Knowledge Base

### 2.1. Общий вид операционной консоли

Раздел **Knowledge Base** → **Документы** представляет собой трёхпанельную операционную консоль.

#### Верхняя панель — toolbar

- **Слева**: статус retrieval backend (`CHROMA`), количество проиндексированных чанков, embedding model.
- **Справа**: кнопки действий:
  - **Загрузить файл** — создать новый документ;
  - **Загрузить версию** — добавить версию к выбранному документу;
  - **Редактировать** — изменить метаданные выбранного документа;
  - **Переиндексировать** — переиндексировать активную версию выбранного документа;
  - **Переиндексировать всё** — массовая переиндексация всех опубликованных документов;
  - **Обновить** — обновить список и детальную панель (также расположена в заголовке консоли рядом с названием).

#### Левая панель — список документов

- Фильтры по статусу, типу, курсу/модулю/теме.
- Поиск по названию/имени файла.
- Пагинация.
- Карточки документов: дата, цветной бейдж статуса, название, версия, количество чанков, embedding model. Клик по карточке выбирает документ.

#### Средняя панель — сводка документа

- Заголовок «СВОДКА ДОКУМЕНТА» + статус публикации.
- **ПАСПОРТ** + **ЭКСПЛУАТАЦИЯ**: технические и пользовательские метаданные документа и активной версии в двух колонках.
- **ВЕРСИИ**: таблица всех версий с кнопками действий.
- **PREVIEW ТЕКСТА**: тоггл **RAW / ОЧИЩЕННЫЙ** + кнопка **Открыть** для полного редактора.
- **ЧАНКИ**: список чанков активной версии с номером, `token_count` и `content_preview`.

#### Правая панель — жизненный цикл

- Хронологическая лента lifecycle-событий: `upload`, `preprocess_start`, `preprocess_done`, `index_start`, `index_done`, `reindex_start`, `reindex_done`, `publish`, `version_activate`, `error` и др.
- Каждое событие содержит: дату/время, статус, длительность (`duration_ms`), описание и технический JSON-снимок (`details`).

### 2.2. Добавление нового материала

1. Откройте Admin Console: `https://curator-admin.alex-n8n.site`.
2. Войдите с Bearer-токеном (`ADMIN_CONSOLE_TOKEN`).
3. Перейдите в раздел **Knowledge Base** → **Документы**.
4. В toolbar нажмите **Загрузить файл**.
5. В модальном окне укажите название, тип документа, курс/модуль/тему, сложность, язык, описание, URL источника и файл.
6. Нажмите **Сохранить документ**.
7. Выберите созданный документ в списке слева.
8. В таблице **ВЕРСИИ** нажмите **Переиндексировать** для chunking, embeddings и индексации в Chroma.
9. После успешной обработки включите публикацию (переключатель / кнопка в блоке публикации).

### 2.3. Обновление версии документа

1. Выберите документ в списке слева.
2. В toolbar нажмите **Загрузить версию**.
3. В модальном окне выберите новый файл и нажмите **Сохранить версию**.
4. Новая версия становится активной автоматически.
5. В таблице **ВЕРСИИ** нажмите **Переиндексировать** в строке активной версии (или в toolbar **Переиндексировать**).

### 2.4. Активация и переиндексация версии

В таблице **ВЕРСИИ** средней панели:

- **Активировать** (для неактивной версии) — делает версию активной и запускает её переиндексацию.
- **Переиндексировать** (для активной версии) — пересчитывает чанки, embeddings и обновляет индекс Chroma.

Toolbar-кнопка **Переиндексировать** выполняет то же действие для активной версии выбранного документа.

### 2.5. Снятие материала с публикации

1. Выберите документ в списке слева.
2. В блоке публикации средней панели (или в toolbar) переключите статус публикации.
3. Документ остаётся в хранилище, но не участвует в retrieval.

### 2.6. Удаление документа

1. Выберите документ в списке слева.
2. Нажмите **Удалить** и подтвердите действие.
3. Документ и все версии мягко удаляются (`status = archived`).

### 2.7. Git workflow для материалов KB

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

### 2.8. Редактирование cleaned-текста

1. В средней панели переключите **PREVIEW ТЕКСТА** в режим **ОЧИЩЕННЫЙ**.
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

### 3.4. Orchestrator Configuration

Раздел **Orchestrator** управляет маршрутизацией запросов студентов: как сообщение классифицируется по intent, какие источники данных используются для каждого intent, ограничениями контекста и token-бюджетами.

#### 3.4.1. Intent Classification

Визуальный редактор `intent_rules`. Для каждого intent задаётся:

- `keywords` — список слов/фраз (одна на строку), при наличии которых запрос относится к intent;
- `priority` — приоритет правила (ниже = выше приоритет);
- `conditions` — логические условия для составных intent (например, `mixed` = `is_org` + `has_keyword: ["итоговый проект"]`).

Конструктор conditions поддерживает:

| Предикат | Значение | Описание |
|----------|----------|----------|
| `is_org` | — | В сообщении найдено хотя бы одно keyword из organizational-правила |
| `is_study` | — | В сообщении найдено хотя бы одно keyword из study-правила |
| `is_progress` | — | В сообщении найдено хотя бы одно keyword из progress-правила |
| `has_keyword` | список строк | В сообщении найдено хотя бы одно из указанных слов |
| `and` | список conditions | Все вложенные условия должны выполниться |

#### 3.4.2. Source Routing

Таблица `intent_source_map` определяет, какие источники используются для каждого intent:

| Intent | LMS | RAG | strict_course | Назначение |
|--------|-----|-----|---------------|------------|
| `deadline` | ✅ | ❌ | ✅ | Только данные LMS |
| `progress` | ✅ | ❌ | ✅ | Только данные LMS |
| `organizational` | ✅ | ❌ | ✅ | Только данные LMS |
| `study` | ❌ | ✅ | ❌ | Только Knowledge Base |
| `mixed` | ✅ | ✅ | ✅ | LMS + Knowledge Base |

#### 3.4.3. Context Limits

| Параметр | По умолчанию | Влияние |
|----------|--------------|---------|
| `max_lms_contents` | 12 | Сколько элементов структуры курса попадает в prompt |
| `max_lms_deadlines` | 5 | Сколько ближайших дедлайнов попадает в prompt |

#### 3.4.4. Token Budgets

| Ключ | По умолчанию | Применение |
|------|--------------|------------|
| `organizational` | 250 | Ответы на организационные вопросы |
| `study_beginner` | 250 | Учебные вопросы для уровня beginner |
| `mixed` | 350 | Смешанные вопросы (LMS + KB) |
| `default` | 300 | Все остальные случаи, включая advanced-study |

Эти значения подобраны так, чтобы при скорости генерации `gpt-4o-mini` ~100 tokens/sec время LLM-вызова не превышало ~3.5 сек, а суммарная latency оставалась в пределах NFR ≤ 5 сек. Если ответы часто обрезаются (`response_truncated_by_max_tokens` в `chat_logs.error` или `llm_truncated=true` в `analytics_events`), бюджет можно увеличить, но это повысит latency.

#### 3.4.5. Fallback Messages

| Ключ | По умолчанию | Когда применяется |
|------|--------------|-------------------|
| `no_lms_data` | «В курсе пока нет опубликованных заданий с дедлайнами…» | Вопрос про дедлайны/задания, но в LMS нет данных |
| `no_rag_context` | «У меня недостаточно данных…» | Study-вопрос, но релевантных материалов KB не найдено |
| `out_of_scope_course` | «У меня нет данных о курсе «{course}»…» | Студент спрашивает про курс, недоступный для его роли |

#### 3.4.6. Рекомендации по настройке

- Не меняйте `intent_source_map` без понимания последствий: LMS — Source of Truth для организационных вопросов, KB — для учебных.
- Для добавления нового типа вопроса используйте `keywords` в существующем intent или создайте новый intent + source map.
- При повреждении конфигурации backend использует жёсткие defaults, совпадающие с текущим хардкодом.

---

## 3.5. Response Cache

AI Curator кэширует ответы на частые запросы, чтобы сократить latency и снизить расходы на LLM/RAG/LMS. Кэш включён по умолчанию и управляется через `RetrievalTuning`.

### Ключ кэша

SHA-256 от нормализованных параметров запроса:

```text
message | role | difficulty | course_id | intent
```

История диалога в ключ не входит: кэш отвечает за последнее сообщение.

### Управление в Admin Console

- **AI & Retrieval Configuration** → параметры `cache_enabled` и `cache_ttl_seconds`.
- `cache_ttl_seconds` по умолчанию **300 секунд** в `RetrievalTuning`; fallback на `CACHE_TTL_SECONDS` (default 86400).

### Инвалидация

Кэш сбрасывается автоматически при изменениях, которые могут повлиять на ответы:

| Действие | Endpoint |
|----------|----------|
| Публикация / снятие с публикации KB | `POST /api/v1/admin/kb/documents/{id}/publish` |
| Обработка / переиндексация документа | `POST /api/v1/admin/kb/documents/{id}/process`, `POST /api/v1/admin/kb/documents/{id}/reindex` |
| Активация / переиндексация версии | `POST /api/v1/admin/kb/documents/{id}/versions/{version_id}/activate`, `/reindex` |
| Сохранение cleaned-текста | `POST /api/v1/admin/kb/documents/{id}/versions/{version_id}/text` |
| Массовая переиндексация | `POST /api/v1/admin/kb/reindex-all`, `POST /api/v1/admin/retrieval/reindex` |
| Изменение AI-конфигурации | `POST /api/v1/admin/ai-config`, `POST /api/v1/admin/ai-config/{id}/activate` |
| Изменение retrieval tuning | `PUT /api/v1/admin/retrieval/tuning` |
| Изменение orchestrator config | `PUT /api/v1/admin/orchestrator/config` |

### Наблюдаемость

- `chat_logs.cache_hit` — `true` для ответов, возвращённых из кэша.
- `execution_sessions.execution_metadata.cache_hit` — флаг в трасировке.
- Operational Logs и Dialog Sessions отображают `cache_hit` в UI/API.

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
| `llm_generate_ms` | LLM generation | < 4000 мс (зависит от `max_tokens`); с текущими бюджетами 250–350 tokens типично 1.5–3 сек |
| `validation_ms` | Answer Validator | < 200 мс |
| `response_cache_ms` | Response cache read/write | < 20 мс |

Общая latency отчитывается в `chat_logs.latency_ms` и в ответе API как `latency_ms`. Дополнительно в `analytics_events.payload` сохраняется флаг `llm_truncated=true`, если ответ обрезался по `finish_reason=length`.

### 4.2. Профилирование вручную

Для замера latency на живом backend выполните изнутри контейнера:

```bash
docker exec ai-curator-backend python /app/scripts/profile_latency.py
```

Скрипт делает 5 вызовов по 6 сценариям (30 запросов) и выводит p50/mean/max.

### 4.3. SLO и NFR

- **NFR-1:** p50 latency на повторных chat-запросах (response cache hit) ≤ **5 секунд**.
- **SLO:** p95 ≤ 8 сек для холодного старта (cache miss + embedding cache miss + LLM cold call).
- **Профилирование Sprint 4 (2026-07-30):** все сценарии уложились в 5 сек; максимальный measured latency — 3547 мс (`study_basic`, холодный старт).
- **Профилирование Sprint D follow-up (2026-08-03):** повторные запросы p50 — 120–133 мс серверного времени (response cache hit), max — 144 мс. Холодный старт с `chunk_size=512` — 3.5–5 сек (advanced ~3.8 сек, beginner ~3.6 сек), что укладывается в SLO ≤ 8 сек.

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
- `GET /api/v1/admin/monitoring/errors`

### 5.1. Виджет «Последние ошибки»

Виджет показывает недавние ошибки и предупреждения обработки запросов. Он объединяет три источника:

1. **`chat_logs.error`** — ошибки LLM и неперехваченные исключения в `Orchestrator.process()`.
2. **`execution_sessions.status`** — статус `error` или `warning` для всего pipeline.
3. **`execution_steps.status`** — статус `error` или `warning` для отдельных стадий (`lms_fetch`, `rag_search` и др.).

Это позволяет увидеть частичные сбои, которые ранее маскировались fallback-ответами. Например, если LMS Adapter недоступен, оркестратор может вернуть стандартный fallback «В курсе пока нет опубликованных заданий…». В `chat_logs.error` записи не будет, но `execution_steps.lms_fetch` получит статус `warning` или `error`, и инцидент отобразится в виджете.

Колонки таблицы:

| Колонка | Описание |
|---------|----------|
| Время | `finished_at` execution-сессии/шага или `created_at` chat_log |
| Источник | `chat_log` / `execution_session` / `execution_step` |
| Status | `error` или `warning` |
| Intent | Классифицированный intent запроса |
| Stage | Стадия pipeline (для `execution_step`) |
| Сообщение | Текст ошибки |
| Session | Business `session_id` (первые 8 символов) |

---

## 6. Логи (Operational Logs)

Раздел **Логи** — операционная консоль запросов студентов. Каждая запись соответствует одному запросу (`chat_requests`) и связанному ответу (`chat_logs`).

### 6.1. Левая панель — список записей

- Фильтры по периоду (24h / 7d / 30d / все), статусу (`ok` / `error` / `pending`) и интенту (`study`, `organizational`, `mixed`, `progress`, `deadline`).
- Поиск по `session_id`.
- Backend-пагинация.
- Карточка записи: дата/время, статус, intent, превью сообщения, `session_id`, роль, курс, latency.

### 6.2. Правая панель — деталь записи

- **Запрос**: `session_id`, `role`, `course_id`, `difficulty`, `intent`, `created_at`.
- **Исполнение**: latency, total tokens, модель LLM, feedback score.
- **Сообщение и ответ**: полный текст запроса и ответа AI, список источников.
- **Ошибка**: блок с текстом ошибки, если ответ завершился ошибкой.
- **LLM calls**: список вызовов LLM с моделью, статусом, latency, tokens; раскрывающийся preview prompt/response trace.
- **Технический снимок (JSON)**: полный JSON детали записи.

### 6.3. Endpoints

- `GET /api/v1/admin/operational-logs` — список operational log entries.
- `GET /api/v1/admin/operational-logs/{id}` — деталь operational log entry.

### 6.4. Dialog Sessions

Раздел **Dialog Sessions** — операционная консоль диалоговых сессий студентов на новой схеме `chat_sessions` + `execution_sessions` + `execution_steps`.

### Структура данных

| Таблица | Назначение |
|---------|------------|
| `chat_sessions` | Каноническая сессия диалога: `session_id`, `user_id`, `role`, `course_id`, `mode` (`text`/`lms`/`rag`/`mixed`), `is_active` |
| `execution_sessions` | Одна трассировка pipeline на каждый chat-запрос. Сохраняет `client_ip`, `user_agent`, `provider_key`, `model_name`, `duration_ms` |
| `execution_steps` | Этапы pipeline: `intent_classify`, `lms_fetch`, `rag_search`, `context_build`, `llm_call`, `answer_validate`, `source_attach`, `response_save` |

**Важно:** миграция старых данных (backfill) не выполняется. Новые таблицы заполняются с момента деплоя. До первых запросов после деплоя консоль будет пуста — это осознанное решение.

### Левая панель — список сессий

- Фильтры: период (`hours`), source mode (`text`/`lms`/`rag`/`mixed`), только активные, поиск по `session_id` / `role`.
- Backend-пагинация.
- Карточка сессии: `session_id`, роль, курс, mode, статус, количество сообщений, время последнего обновления.

### Правая панель — сводка сессии

- **Параметры сессии**: `session_id`, visitor IP, роль, курс, сложность, mode, активность.
- **Параметры исполнения**: `provider_key`, `model_name`, latency, status, source.
- **Memory policy / limits**: снапшот активной AI-конфигурации (`model`, `max_tokens`, `temperature`), `memory_source: PostgreSQL`.
- **Таблица turns**: пары «запрос пользователя / ответ системы» с cache hit, response time, tokens.
- **Аккордеон «Таймлайн execution pipeline»**: этапы `execution_steps` с duration, status и JSON-метаданными.
- **Технический снимок диалога (JSON)**: полный payload detail-ответа.

Endpoints:

- `GET /api/v1/admin/dialog-sessions` — список `ChatSession`.
- `GET /api/v1/admin/dialog-sessions/{session_id}` — деталь: turns + execution sessions + budget + memory_source.

---

## 7. Аудит

**Политика:** в `audit_logs` фиксируются только **изменяющие административные действия** и публичные `chat_request`. Read-only просмотры консолей (`GET /api/v1/admin/*`) намеренно не аудитируются, чтобы журнал не порождал сам себя при каждом открытии страницы.

Доступные endpoints:

- `GET /api/v1/admin/audit` — журнал аудита с фильтрами (возвращает объект `{items, total, limit, offset}`).
- `GET /api/v1/admin/audit/{id}` — деталь audit-записи.

### Расширенные поля аудита

| Поле | Назначение |
|------|------------|
| `user_name` | Имя пользователя, выполнившего действие |
| `ip_address` | IP-адрес клиента, с которого пришёл запрос |

### Фильтры журнала

- `action`, `resource_type`, `user_id` (сопоставляется с `user_id` и `user_name`);
- `date_from` / `date_to` — фильтр по диапазону дат (ISO `YYYY-MM-DD`).

Для просмотра только запросов студентов используйте фильтр `action=chat_request`. Для административных действий отфильтруйте `action` известными значениями (`create`, `update`, `delete`, `publish`, `unpublish`, `process`, `reindex`, `activate_version`, `save_cleaned_text` и т.п.).

### Детальная карточка

Правая панель консоли аудита показывает: пользователя (ID + имя), IP-адрес, время, действие, ресурс, ID ресурса и JSON snapshot `details`.

### Endpoints

- `GET /api/v1/admin/audit` — список с фильтрами.
- `GET /api/v1/admin/audit/{id}` — детальная карточка.

---

## 8. Переменные окружения

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
| `TEST_DATABASE_URL` | Отдельная PostgreSQL для тестов (обязательно; не должна совпадать с `DATABASE_URL`) |
| `PYTEST_ALLOW_PROD_DB` | Разрешить pytest fallback на `DATABASE_URL`, если `TEST_DATABASE_URL` не задан (`true`/`false`) |

| `CHROMA_COLLECTION_NAME` | Продакшен коллекция Chroma (`ai_curator_kb`) |
| `CHROMA_TEST_COLLECTION_NAME` | Тестовая коллекция Chroma (`ai_curator_kb_test`) |
| `CACHE_FILE_PATH` | Путь к JSON-файлу кэша ответов (`/app/storage/cache/response_cache.json`) |
| `CACHE_TTL_SECONDS` | TTL ответов по умолчанию, когда `RetrievalTuning.cache_ttl_seconds` не задан (86400) |

### AI Config tuning для latency

В Admin Console можно влиять на latency через параметры активной конфигурации:

| Параметр | Влияние на latency | Рекомендация |
|----------|-------------------|--------------|
| `max_tokens` | Жёсткий потолок длины ответа LLM | Для chat ограничен кодом через `orchestrator_configs.intent_max_tokens`: `organizational`=250, `study_beginner`=250, `mixed`=350, `default`=300 |
| `top_k_retrieval` | Сколько RAG-чанков попадает в prompt | Для chat переопределяется кодом до 3; для Admin оставить 5 |
| `intent_max_tokens` | Бюджет completion tokens по intent | Настраивается в Admin Console → Orchestrator; снижение ускоряет ответ, но при слишком низком значении возможно `response_truncated_by_max_tokens` |
| `rag_distance_threshold` | Фильтр шумных чанков | **0.6** в текущей конфигурации. Было 1.35 — при этом пороге RAG возвращал нерелевантные материалы (например, уроки Claude Code по запросу «Fine-Tuning»), и LLM либо отказывалась отвечать на фоне ложных источников, либо давала общее определение из своих знаний. Уменьшение до 0.6 отсекло шум и улучшило точность source attribution. |
| `course_boost_enabled` | Приоритизировать чанки, совпадающие по `course_id` | `true` — для учебных вопросов мягко повышает ранг материалов текущего курса, не отсекая общие материалы |
| `course_boost_factor` | Сила курсового буста | 0.15 по умолчанию; 0 — отключить влияние `course_id` на ранжирование |
| `system_prompt` + `output_rules` | Размер prompt | Избыточный текст увеличивает prompt tokens и latency |
| `max_history_messages` | Длина истории в prompt | Меньше сообщений — меньше токенов |

### AI Config — default instructions backfill

Backend автоматически подставляет дефолтные значения в `beginner_instructions` и `advanced_instructions`, если активная конфигурация не содержит этих полей (`NULL` или пустая строка). Это защищает от ситуации, когда учебный вопрос для beginner получает отказ из-за отсутствия чёткой инструкции отвечать на основе контекста.

Рекомендуемое содержание `beginner_instructions`:

```text
Уровень подготовки: beginner. Объясняй простыми словами, избегай жаргона, давай конкретные примеры и аналогии. Не используй таблицы, не приводи код, не упоминай Big-O или сложность алгоритмов. Не углубляйся в технические детали. Обязательно отвечай на основе предоставленных материалов; если контекст неполный — всё равно дай краткий ответ на том, что есть. Не отказывайся от ответа, когда предоставлен релевантный контекст.
```

Рекомендуемое содержание `advanced_instructions`:

```text
Уровень подготовки: advanced. Дай структурированный углублённый ответ в формате: краткое определение, ключевые отличия списком, 1-2 конкретных примера кода на Python, практические нюансы и типичные ошибки. Используй markdown (заголовки, списки, выделение). Без таблиц, без Big-O, без длинных разборов edge cases. Примеры должны быть техническими и конкретными, но лаконичными.
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

## 9. Retention и архивы

### 9.1. Политика хранения

AI Curator разделяет эксплуатационные данные на две категории с разными сроками хранения:

| Категория | Таблицы | Срок хранения | Переменная |
|-----------|---------|---------------|------------|
| **Hot logs** | `chat_requests`, `chat_logs`, `analytics_events`, `audit_logs`, `llm_calls` | 30 дней | `HOT_RETENTION_DAYS` |
| **LLM traces** | `llm_call_traces` (полные prompt/response) | 7 дней | `TRACE_RETENTION_DAYS` |

По достижении срока записи архивируются в `ARCHIVE_DIR` как gzip-сжатые JSON Lines и удаляются из PostgreSQL.

### 9.2. Архивы

Файлы архивов именуются по шаблону:

```text
{table_name}_{cutoff_iso_timestamp}.jsonl.gz
```

Примеры:

```text
chat_requests_2026-07-06T00:00:00+00:00.jsonl.gz
llm_call_traces_2026-07-29T00:00:00+00:00.jsonl.gz
```

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

### 9.3. Расписание cleanup

Cleanup запускается фоновой задачей `main.py::_retention_cleanup_loop()`:

- Интервал: раз в 24 часа.
- При ошибке: повторная попытка через 1 час.
- Задача не должна падать основное приложение.
- Сам cleanup фиксируется в `audit_logs` как `action=retention_cleanup`, `resource_type=system`.

### 9.4. Экспорт логов

Помимо автоматической ротации, администратор может выгрузить логи в CSV из Admin Console:

| Раздел | Endpoint | Описание |
|--------|----------|----------|
| Логи | `POST /api/v1/admin/operational-logs/export` | Запросы студентов, intent, latency, source_type |
| Журнал аудита | `POST /api/v1/admin/audit/export` | Административные действия и chat-запросы |
| Диалоги | `POST /api/v1/admin/dialog-sessions/export` | Сводка по диалоговым сессиям |

Особенности:

- Export endpoints **read-only**, они не изменяют данные и не пишут в audit log.
- Export доступен как с полным admin-токеном, так и с **demo-токеном** Admin Console. Это осознанное решение: демо-пользователь может просматривать и выгружать логи, но не может выполнять мутации.
- CSV-файл генерируется на лету и скачивается в браузере; на сервере не сохраняется.
- Лимит записей в одном файле: до 10 000 для operational logs / audit, до 10 000 для dialog sessions.

## 10. Тестирование

Подробный контракт тестирования — в `docs/TESTING_CONTRACT.md`. Краткая сводка:

| Маркер | Что проверяет | Команда |
|--------|--------------|---------|
| `unit` | Быстрые тесты без внешних сетевых вызовов | `pytest tests/ -m unit -q` |
| `integration` | Интеграции с LMS, RAG, Chroma, chat pipeline | `pytest tests/ -m integration -q` |
| `expensive` | Дорогие LLM-тесты (зарезервированы) | `pytest tests/ -m expensive -q` |
| (все) | Полный прогон | `pytest tests/ -q` |

### Требования к окружению

- `TEST_DATABASE_URL` — отдельная PostgreSQL, например `ai_curator_test`. Никогда не должна совпадать с `DATABASE_URL`.
- `PYTEST_ALLOW_PROD_DB=false` в production и `.env.example`.
- `CHROMA_TEST_COLLECTION_NAME` — изолированная тестовая коллекция (по умолчанию `ai_curator_kb_test`).

### Запуск внутри backend-контейнера

```bash
docker compose exec ai-curator-backend pytest tests/ -m unit -q
docker compose exec ai-curator-backend pytest tests/ -m integration -q
docker compose exec ai-curator-backend pytest tests/ -q
```

### Защита от случайного использования боевой БД

Если `TEST_DATABASE_URL` не задана и `PYTEST_ALLOW_PROD_DB` не `true`, pytest завершается с ошибкой:

```
TEST_DATABASE_URL is not configured. Set TEST_DATABASE_URL to a dedicated test database,
or set PYTEST_ALLOW_PROD_DB=true to intentionally use the production database for tests.
```

## 11. История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-08-03 | 2.5 | Обновлён раздел 4 «Latency»: уточнены NFR/SLO (повторные запросы ≤ 5 сек, холодный старт ≤ 8 сек); актуальные результаты профилирования Sprint D follow-up; token-бюджеты в Orchestrator Configuration снижены до 250–350 tokens; размер KB-чанков возвращён к 512 tokens с переиндексацией; добавлена метрика `response_cache_ms`; добавлен флаг `llm_truncated` в analytics; обновлены рекомендуемые `beginner_instructions` и `advanced_instructions` |
| 2026-08-01 | 1.9 | Добавлен подраздел 6.4 «Dialog Sessions» с описанием консоли диалогов и endpoints `GET /api/v1/admin/dialog-sessions` / `{session_id}` |
| 2026-08-01 | 2.0 | Реструктуризация Dialog Sessions под схему `chat_sessions` + `execution_sessions` + `execution_steps`; обновлена структура консоли и описание timeline pipeline; раздел 7 «Аудит» дополнен полями `user_name`/`ip_address`, фильтрами по дате и детальной карточкой |
| 2026-08-01 | 2.1 | `GET /api/v1/admin/audit` возвращает `{items, total, limit, offset}`; `POST /api/v1/chat` фиксирует `client_ip` и `user_agent` в `ExecutionSession`; в консоли Dialog Sessions отображается visitor IP и source |
| 2026-08-01 | 2.2 | `POST /api/v1/chat` создаёт audit-запись `chat_request` с `session_id`, ролью студента и `ip_address`; в Журнале аудита можно отфильтровать запросы студентов по `action=chat_request` |
| 2026-08-02 | 2.4 | Добавлен раздел 3.5 «Response Cache»: ключ кэша, инвалидация, наблюдаемость; добавлены переменные `CACHE_FILE_PATH` и `CACHE_TTL_SECONDS` |
| 2026-08-05 | 2.5 | Расширен раздел 9 «Retention и архивы»: явная политика hot logs 30 дней / traces 7 дней, расписание cleanup, архивы JSONL.GZ; добавлен раздел 9.4 «Экспорт логов» с CSV export endpoints и правилом доступа в demo-режиме |
| 2026-08-02 | 2.3 | Убран аудит read-only действий; раздел 7 Аудит описывает новую политику: только изменяющие действия и `chat_request` |
| 2026-07-30 | 1.0 | Создан документ |
 | 2026-07-30 | 1.1 | Добавлены расширенные параметры AI Config, retention и архивирование логов |
| 2026-07-30 | 1.2 | Добавлен раздел мониторинга latency: метрики из `analytics_events`, ручное профилирование через `scripts/profile_latency.py`, SLO/NFR, AI Config tuning для latency |
| 2026-07-30 | 1.3 | Добавлен раздел AI Config default instructions backfill; задокументировано устранение критичного дефекта beginner-ответов в Sprint 4 |
| 2026-07-31 | 1.4 | Добавлен раздел 2.5 «Git workflow для материалов KB» и переменные окружения KB Content Git |
| 2026-07-31 | 1.5 | Актуализирован раздел 2 под трёхпанельную операционную консоль KB Documents; добавлены подразделы про toolbar, ПАСПОРТ/ЭКСПЛУАТАЦИЯ, PREVIEW ТЕКСТА, ЧАНКИ и lifecycle |
| 2026-07-31 | 1.6 | В таблицу AI Config tuning добавлены параметры `course_boost_enabled` и `course_boost_factor` для мягкой приоритизации курсовых материалов в RAG |
| 2026-07-31 | 1.7 | Добавлен раздел 3.4 «Orchestrator Configuration» с описанием интент-классификации, source routing, context limits, token budgets и fallback messages |
