# ⚙️ OPERATIONS.md — AI Curator

**Проект:** ai-curator  
**Версия:** 1.8
**Дата:** 2026-08-05
**Статус:** Актуален: Knowledge Base, AI и Retrieval, Orchestrator, Dialog Sessions, Audit, Response Cache, retention, CSV export

---

## 🎯 1. Назначение

Руководство по эксплуатации AI Curator: обновление Knowledge Base, управление AI-конфигурацией и retrieval, настройка Orchestrator, просмотр аналитики, мониторинга и операционных логов.

---

## 📚 2. Knowledge Base

### 🧩 2.1. Общий вид операционной консоли

Раздел **База знаний** → **Документы** представляет собой трёхпанельную операционную консоль.

#### 🧰 Верхняя панель — toolbar

- **Слева**: статус retrieval backend (`CHROMA`), количество проиндексированных чанков, embedding model.
- **Справа**: кнопки действий:
  - **Загрузить файл** — создать новый документ;
  - **Загрузить версию** — добавить версию к выбранному документу;
  - **Редактировать** — изменить метаданные выбранного документа;
  - **Переиндексировать** — переиндексировать активную версию выбранного документа;
  - **Переиндексировать всё** — массовая переиндексация всех документов;
  - **Обновить** — обновить список и детальную панель.

#### 📋 Левая панель — список документов

- Фильтры по статусу и типу документа.
- Поиск по названию, типу, статусу или ID.
- Пагинация.
- Карточки документов: дата, цветной бейдж статуса, название, версия, количество чанков, embedding model. Клик по карточке выбирает документ.

#### 📄 Средняя панель — сводка документа

- Заголовок «СВОДКА ДОКУМЕНТА» + статус обработки + бейдж «Опубликован», если документ опубликован.
- **ПАСПОРТ** + **ЭКСПЛУАТАЦИЯ**: технические и пользовательские метаданные документа и активной версии в двух колонках.
- **ВЕРСИИ**: таблица всех версий с кнопками действий.
- **PREVIEW ТЕКСТА**: тоггл **RAW / ОЧИЩЕННЫЙ** + кнопка **Открыть** для полного редактора.
- **ЧАНКИ**: список чанков активной версии с номером, `token_count` и `content_preview`.

#### 🕒 Правая панель — жизненный цикл

- Хронологическая лента lifecycle-событий: `upload`, `preprocess_start`, `preprocess_done`, `index_start`, `index_done`, `reindex_start`, `reindex_done`, `publish`, `version_activate`, `error` и др.
- Каждое событие содержит: дату/время, статус, длительность (`duration_ms`), описание и технический JSON-снимок (`details`).

### 📥 2.2. Добавление нового материала

1. Откройте Admin Console: `https://curator-admin.alex-n8n.site`.
2. Войдите с Bearer-токеном (`ADMIN_CONSOLE_TOKEN`).
3. Перейдите в раздел **База знаний** → **Документы**.
4. В toolbar нажмите **Загрузить файл**.
5. В форме укажите название, тип документа, ID курса/модуля/темы, язык, описание, URL источника и файл.
6. Нажмите **Сохранить документ**.
7. Выберите созданный документ в списке слева.
8. В таблице **ВЕРСИИ** нажмите **Переиндексировать** для chunking, embeddings и индексации в Chroma.
9. После успешной индексации документ становится доступен для ответов.

### 🔄 2.3. Обновление версии документа

1. Выберите документ в списке слева.
2. В toolbar нажмите **Загрузить версию**.
3. В модальном окне выберите новый файл и нажмите **Загрузить версию**.
4. Новая версия появится в таблице **ВЕРСИИ**.
5. Активируйте новую версию кнопкой **Активировать**; затем нажмите **Переиндексировать** в строке активной версии.

### ▶️ 2.4. Активация и переиндексация версии

В таблице **ВЕРСИИ** средней панели:

- **Активировать** (для неактивной версии) — делает версию активной.
- **Переиндексировать** (для активной версии) — пересчитывает чанки, embeddings и обновляет индекс Chroma.

Toolbar-кнопка **Переиндексировать** выполняет то же действие для активной версии выбранного документа.

### ✏️ 2.5. Редактирование cleaned-текста

1. В средней панели переключите **PREVIEW ТЕКСТА** в режим **ОЧИЩЕННЫЙ**.
2. Нажмите **Открыть**.
3. Отредактируйте текст в модальном редакторе.
4. Нажмите **Сохранить и переиндексировать**.
5. Backend сохранит новый cleaned-текст в файловом хранилище, обновит `sha256` и пересчитает чанки.

> **Примечание:** публикация / снятие с публикации и удаление документов реализованы в Admin API (`POST /api/v1/admin/kb/documents/{id}/publish`, `DELETE /api/v1/admin/kb/documents/{id}`), но не вынесены в UI Admin Console текущей версии. См. roadmap в `docs/PROJECT_STATE.md`.

---

## 🤖 3. AI и Retrieval

### ⚙️ 3.1. Панель AI и Retrieval

В Sidebar Admin Console раздел называется **AI и Retrieval**. Это единая панель, объединяющая настройки LLM-провайдеров, параметры retrieval и поведение модели.

Кнопка **Сохранить** в правом верхнем углу:
- создаёт новую версию AI-конфигурации и активирует её автоматически;
- одновременно обновляет `RetrievalTuning` (без создания отдельных версий).

В демо-режиме (`ADMIN_CONSOLE_DEMO_TOKEN`) кнопка **Сохранить** и кнопки мутаций отключены; backend вернёт `403` на любое изменяющее действие.

### 🔌 3.2. LLM-провайдеры

Секция **LLM-провайдеры и активность** позволяет настроить:

- **Активный провайдер** — `openai` или `gigachat`.
- **Fallback провайдер** — провайдер, который используется при сбое активного.
- Карточки провайдеров:
  - статус (`ACTIVE`, `FALLBACK`, `READY` / `NOT READY`);
  - Base URL / Endpoint;
  - Model (OpenAI: `gpt-4o-mini`, `gpt-4o`; GigaChat: `GigaChat-Max`);
  - Temperature (0–2);
  - Max tokens;
  - флаг **Включён**;
  - кнопка **Проверить** — тестовый вызов провайдера.

### 🔍 3.3. Параметры поиска

Секция **Параметры поиска** управляет retrieval и кэшем:

| Параметр | Описание |
|----------|----------|
| `top_k` | Сколько RAG-чанков попадает в prompt (1–20). Для chat backend переопределяет до 3 для `study`/`mixed`. |
| `rag_distance_threshold` | Порог cosine distance; чанки с большим расстоянием отсекаются как шум. |
| `chunk_size` | Размер чанка при индексации (128–8192). |
| `chunk_overlap` | Перекрытие соседних чанков; должен быть меньше `chunk_size`. |
| `cache_enabled` | Включить/выключить Response Cache. |
| `cache_ttl_seconds` | Время жизни кэш-записи в секундах (30–86400). |
| `retrieval_timeout_ms` | Таймаут RAG-операций. |
| `embedding_timeout_ms` | Таймаут embedding-вызовов. |
| `course_boost_enabled` | Приоритизировать чанки текущего курса. |
| `course_boost_factor` | Сила курсового буста (0–1). |

### 🧠 3.4. Поведение

Секция **Поведение** содержит текстовые поля (открываются в модальном редакторе):

- **Системный промпт** — обязательное поле.
- **Правила ответа** (`output_rules`).
- **Текст отказа** (`refusal_answer_text`).
- **Max history messages** — лимит сообщений истории в prompt (0–50).

### 🎓 3.5. Инструкции

Секция **Инструкции** содержит:

- **Инструкции для начинающих** (`beginner_instructions`).
- **Инструкции для продвинутых** (`advanced_instructions`).
- **Few-shot примеры** (`few_shot_examples`).

Backend автоматически подставляет дефолтные `beginner_instructions` и `advanced_instructions`, если активная конфигурация не содержит этих полей.

---

## 🧭 4. Orchestrator Configuration

Раздел **Оркестратор** управляет маршрутизацией запросов студентов: как сообщение классифицируется по intent, какие источники данных используются для каждого intent, ограничениями контекста и token-бюджетами.

### 🏷️ 4.1. Intent Classification

Визуальный редактор `intent_rules`. Для каждого intent задаётся:

- `keywords` — список слов/фраз (одна на строку), при наличии которых запрос относится к intent;
- `priority` — приоритет правила (меньше число — выше приоритет). Применяется только к интентам, определённым через conditions. `deadline` и `progress` определяются по keywords раньше и не участвуют в сравнении priority;
- **Дополнительно** — чекбоксы, требующие наличия keywords другого типа (`is_org`, `is_study`, `is_progress`). Если выбрано несколько чекбоксов, backend строит составное условие `{and: [...]}`.

### 🔀 4.2. Source Routing

Таблица **Маршрутизация источников** определяет, какие источники используются для каждого intent:

| Intent | LMS | RAG | strict_course | Назначение |
|--------|-----|-----|---------------|------------|
| `deadline` | ✅ | ❌ | ✅ | Только данные LMS |
| `progress` | ✅ | ❌ | ✅ | Только данные LMS |
| `organizational` | ✅ | ❌ | ✅ | Только данные LMS |
| `study` | ❌ | ✅ | ❌ | Только Knowledge Base |
| `mixed` | ✅ | ✅ | ✅ | LMS + Knowledge Base |

### 📐 4.3. Context Limits

| Параметр | По умолчанию | Влияние |
|----------|--------------|---------|
| `max_lms_contents` | 12 | Сколько элементов структуры курса попадает в prompt |
| `max_lms_deadlines` | 5 | Сколько ближайших дедлайнов попадает в prompt |

### 💰 4.4. Token Budgets

| Ключ | По умолчанию | Применение |
|------|--------------|------------|
| `organizational` | 500 | Ответы на организационные вопросы |
| `study_beginner` | 650 | Учебные вопросы для уровня beginner |
| `mixed` | 800 | Смешанные вопросы (LMS + KB) |
| `default` | 750 | Все остальные случаи, включая advanced-study |

Эти значения подобраны так, чтобы при скорости генерации `gpt-4o-mini` ~100 tokens/sec время LLM-вызова не превышало ~5–8 сек, а суммарная latency оставалась в пределах NFR ≤ 8 сек. Если ответы часто обрезаются (`response_truncated_by_max_tokens` в `chat_logs.error` или `llm_truncated=true` в `analytics_events`), бюджет можно увеличить, но это повысит latency.

### 💬 4.5. Fallback Messages

| Ключ | По умолчанию | Когда применяется |
|------|--------------|-------------------|
| `no_lms_data` | «В курсе пока нет опубликованных заданий с дедлайнами…» | Вопрос про дедлайны/задания, но в LMS нет данных |
| `no_rag_context` | «У меня недостаточно данных…» | Study-вопрос, но релевантных материалов KB не найдено |
| `out_of_scope_course` | «У меня нет данных о курсе «{course}»…» | Студент спрашивает про курс, недоступный для его роли |

### 💡 4.6. Рекомендации по настройке

- Не меняйте `intent_source_map` без понимания последствий: LMS — Source of Truth для организационных вопросов, KB — для учебных.
- Для добавления нового типа вопроса используйте `keywords` в существующем intent или создайте новый intent + source map.
- При повреждении конфигурации backend использует жёсткие defaults, совпадающие с хардкодом в `src/models/orchestrator_config.py`.

---

## 💾 5. Response Cache

AI Curator кэширует ответы на частые запросы, чтобы сократить latency и снизить расходы на LLM/RAG/LMS. Кэш включён по умолчанию и управляется через **AI и Retrieval** → параметры `cache_enabled` и `cache_ttl_seconds`.

### 🔑 5.1. Ключ кэша

SHA-256 от нормализованных параметров запроса:

```text
message | role | difficulty | course_id | intent
```

История диалога в ключ не входит: кэш отвечает за последнее сообщение.

### 🎮 5.2. Управление в Admin Console

- **AI и Retrieval Configuration** → параметры `cache_enabled` и `cache_ttl_seconds`.
- `cache_ttl_seconds` по умолчанию **300 секунд** в `RetrievalTuning`; fallback на `CACHE_TTL_SECONDS` (default 86400).

### 🔄 5.3. Инвалидация

Кэш сбрасывается автоматически при изменениях, которые могут повлиять на ответы:

| Действие | Endpoint |
|----------|----------|
| Обработка / переиндексация документа | `POST /api/v1/admin/kb/documents/{id}/process`, `POST /api/v1/admin/kb/documents/{id}/reindex` |
| Активация / переиндексация версии | `POST /api/v1/admin/kb/documents/{id}/versions/{version_id}/activate`, `/reindex` |
| Сохранение cleaned-текста | `POST /api/v1/admin/kb/documents/{id}/versions/{version_id}/text` |
| Массовая переиндексация | `POST /api/v1/admin/kb/reindex-all`, `POST /api/v1/admin/retrieval/reindex` |
| Изменение AI-конфигурации | `POST /api/v1/admin/ai-config`, `POST /api/v1/admin/ai-config/{id}/activate` |
| Изменение retrieval tuning | `PUT /api/v1/admin/retrieval/tuning` |
| Изменение orchestrator config | `PUT /api/v1/admin/orchestrator/config` |

> Публикация / снятие с публикации KB (`POST /api/v1/admin/kb/documents/{id}/publish`) инвалидирует кэш на уровне API, но в текущей версии UI не представлено кнопкой управления публикацией.

### 👁️ 5.4. Наблюдаемость

- `chat_logs.cache_hit` — `true` для ответов, возвращённых из кэша.
- `execution_sessions.execution_metadata.cache_hit` — флаг в трасировке.
- Логи и Диалоги отображают `cache_hit` в UI/API.

---

## 📈 6. Аналитика

Раздел **Аналитика запросов** содержит:

- ключевые метрики: Всего запросов, Ответов, Средняя задержка, % отвеченных, Без ответа, Ошибки чата (%);
- распределение запросов по темам (intent);
- источники ответов (LMS, База знаний, Кэш, Fallback, Ошибка);
- latency histogram и сводку задержек (avg/median/p95/p99);
- список вопросов без ответа.

Аналитика читается из PostgreSQL: таблицы `chat_requests`, `chat_logs`, `analytics_events`.

### 🔍 6.1. Фильтры

- **С / По** — диапазон дат.
- **Курс** — фильтр по `course_id`.
- Пресеты: **7 дней**, **30 дней**.
- Кнопка **CSV** — экспорт аналитического отчёта.

### ⏱️ 6.2. Мониторинг latency

Каждый chat-ответ записывает полную разбивку latency в `analytics_events.payload.timings_ms`:

| Метрика | Компонент | Целевое значение |
|---------|-----------|------------------|
| `intent_detect_ms` | Классификация | < 10 мс |
| `lms_deadlines_ms` / `lms_progress_ms` / `lms_contents_ms` | LMS Adapter | параллельно, сумма не критична; каждый < 3 сек |
| `rag_embedding_ms` | RAG embedding (кэш или OpenAI) | < 1000 мс холодный, < 10 мс из кэша |
| `rag_chroma_ms` | Chroma query | < 500 мс |
| `rag_postprocess_ms` | Фильтрация + дедупликация | < 50 мс |
| `llm_generate_ms` | LLM generation | < 4000 мс (зависит от `max_tokens`); с текущими бюджетами 500–800 tokens типично 2–5 сек |
| `validation_ms` | Answer Validator | < 200 мс |
| `response_cache_ms` | Response cache read/write | < 20 мс |

Общая latency отчитывается в `chat_logs.latency_ms` и в ответе API как `latency_ms`. Дополнительно в `analytics_events.payload` сохраняется флаг `llm_truncated=true`, если ответ обрезался по `finish_reason=length`.

### 🛠️ 6.3. Профилирование вручную

Для замера latency на живом backend выполните изнутри контейнера:

```bash
docker exec ai-curator-backend python /app/scripts/profile_latency.py
```

Скрипт делает 5 вызовов по 6 сценариям (30 запросов) и выводит p50/mean/max.

### 🎯 6.4. SLO и NFR

- **NFR-1:** p50 latency на повторных chat-запросах (response cache hit) ≤ **5 секунд**.
- **SLO:** p95 ≤ 8 сек для холодного старта (cache miss + embedding cache miss + LLM cold call).
- **Профилирование Sprint 4 (2026-07-30):** все сценарии уложились в 5 сек; максимальный measured latency — 3547 мс (`study_basic`, холодный старт).
- **Профилирование Sprint D follow-up (2026-08-03):** повторные запросы p50 — 120–133 мс серверного времени (response cache hit), max — 144 мс. Холодный старт с `chunk_size=512` — 3.5–5 сек (advanced ~3.8 сек, beginner ~3.6 сек), что укладывается в SLO ≤ 8 сек.

---

## 📊 7. Мониторинг

Раздел **Панель состояния** отображает статус:

- API;
- PostgreSQL;
- LMS-интеграции;
- Chroma (векторного индекса);
- OpenAI;
- GigaChat.

Также доступны JSON endpoints:

- `GET /api/v1/admin/monitoring/status`
- `GET /api/v1/admin/monitoring/health`
- `GET /api/v1/admin/monitoring/errors`

### 🚨 7.1. Виджет «Последние ошибки»

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
| Сессия | Business `session_id` (первые 8 символов) |

---

## 📜 8. Логи (Operational Logs)

Раздел **Логи** — операционная консоль запросов студентов. Каждая запись соответствует одному запросу (`chat_requests`) и связанному ответу (`chat_logs`).

### 📋 8.1. Левая панель — список записей

- Фильтры по периоду: **24h / 7d / 30d / все**.
- Фильтры по статусу: **все / успешно / ошибка / ожидание**.
- Фильтры по интенту: **все / учебный / организационный / смешанный / прогресс / дедлайн / не распределено**.
- Фильтры по источнику: **все / LMS / База знаний / LMS + База знаний / Кэш / Fallback / Ошибка**.
- Поиск по `session_id`.
- Backend-пагинация.
- Карточка записи: дата/время, статус, intent, cache-hit, превью сообщения, `session_id`, роль, курс, latency.

### 📄 8.2. Правая панель — деталь записи

- **Параметры запроса**: сессия, роль, курс, сложность, создано.
- **Параметры исполнения**: интент, latency, токены, модель LLM, оценка, cache hit.
- **Цепочка этапов**: краткая последовательность стадий pipeline.
- **Запрос пользователя / ответ системы**: полный текст с источниками.
- **Ошибка**: блок с текстом ошибки, если ответ завершился ошибкой.
- **Таймлайн pipeline**: этапы с timestamp, статусом, offset, длительностью и JSON payload. Для RAG-этапа доступна кнопка «Показать чанки».
- **Технический снимок (JSON)**: полный JSON детали записи.

### 🔌 8.3. Endpoints

- `GET /api/v1/admin/operational-logs` — список operational log entries.
- `GET /api/v1/admin/operational-logs/{id}` — деталь operational log entry.
- `POST /api/v1/admin/operational-logs/export` — экспорт в CSV.

---

## 💬 9. Диалоги (Dialog Sessions)

Раздел **Диалоги** — операционная консоль диалоговых сессий студентов на схеме `chat_sessions` + `execution_sessions` + `execution_steps`.

### 🗂️ 9.1. Структура данных

| Таблица | Назначение |
|---------|------------|
| `chat_sessions` | Каноническая сессия диалога: `session_id`, `user_id`, `role`, `course_id`, `mode` (`text`/`lms`/`rag`/`mixed`), `is_active` |
| `execution_sessions` | Одна трассировка pipeline на каждый chat-запрос. Сохраняет `client_ip`, `user_agent`, `provider_key`, `model_name`, `duration_ms` |
| `execution_steps` | Этапы pipeline: `intent_classify`, `lms_fetch`, `rag_search`, `context_build`, `llm_call`, `answer_validate`, `source_attach`, `response_save` |

**Важно:** миграция старых данных (backfill) не выполняется. Новые таблицы заполняются с момента деплоя. До первых запросов после деплоя консоль будет пуста — это осознанное решение.

### 📋 9.2. Левая панель — список сессий

- Фильтры: период (**24h / 7d / 30d / все**), source mode (**все / текст / LMS / RAG / mixed**), активность (**все / активные / неактивные**), поиск по `session_id` / `role`.
- Backend-пагинация.
- Карточка сессии: `session_id`, роль, курс, mode, статус, количество сообщений, время последнего обновления.

### 📄 9.3. Правая панель — сводка сессии

- **Параметры сессии**: сессия, IP, режим (`mode`), активна, сообщений, обменов, обновлена.
- **Параметры исполнения**: используется ли RAG, провайдер / модель, время ответа, источник памяти (`memory_source`), маршрут, cache hit.
- **Лимиты / политика**: снапшот активной AI-конфигурации (`model`, `max_tokens`, `temperature`).
- **Таблица turns**: пары «запрос пользователя / ответ системы» с режимом, временем ответа, кэшем, моделью и временем запроса.
- **Таймлайн execution pipeline**: этапы `execution_steps` с duration, status и JSON-метаданными.
- **Технический снимок диалога (JSON)**: полный payload detail-ответа.

### 🔌 9.4. Endpoints

- `GET /api/v1/admin/dialog-sessions` — список `ChatSession`.
- `GET /api/v1/admin/dialog-sessions/{session_id}` — деталь: turns + execution sessions + budget + memory_source.
- `POST /api/v1/admin/dialog-sessions/export` — экспорт в CSV.

---

## 📋 10. Журнал аудита

**Политика:** в `audit_logs` фиксируются только **изменяющие административные действия** и публичные `chat_request`. Read-only просмотры консолей (`GET /api/v1/admin/*`) намеренно не аудитируются, чтобы журнал не порождал сам себя при каждом открытии страницы.

### 🔍 10.1. Фильтры журнала

- **Окно времени**: 24h / 7d / 30d / все.
- **action** — фильтр по действию.
- **resource_type** — фильтр по типу ресурса.
- **Поиск по user_id или user_name**.
- Backend-пагинация.

Для просмотра только запросов студентов используйте фильтр `action=chat_request`. Для административных действий отфильтруйте `action` известными значениями (`create`, `update`, `delete`, `publish`, `unpublish`, `process`, `reindex`, `activate_version`, `save_cleaned_text` и т.п.).

### 🪪 10.2. Детальная карточка

Правая панель консоли аудита показывает:

- **Параметры акции**: ID акции, тип акции (`action`), ID ресурса, тип ресурса.
- **Параметры пользователя**: ID пользователя, имя пользователя, IP-адрес, дата события.
- **Детали / metadata**: JSON деталей действия.
- **Технический снимок события (JSON)**: полный payload audit-записи.

### 🔌 10.3. Endpoints

- `GET /api/v1/admin/audit` — журнал аудита с фильтрами (возвращает объект `{items, total, limit, offset}`).
- `GET /api/v1/admin/audit/{id}` — деталь audit-записи.
- `POST /api/v1/admin/audit/export` — экспорт в CSV.

---

## 🔧 11. Переменные окружения

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

### ⚡ 11.1. AI Config tuning для latency

В Admin Console можно влиять на latency через параметры активной конфигурации:

| Параметр | Влияние на latency | Рекомендация |
|----------|-------------------|--------------|
| `max_tokens` (в provider settings) | Жёсткий потолок длины ответа LLM | Задаётся отдельно для OpenAI и GigaChat; реальная длина ответа дополнительно ограничивается `intent_max_tokens` в Orchestrator |
| `top_k` | Сколько RAG-чанков попадает в prompt | Для chat backend переопределяет до 3; для Admin оставить 5 |
| `intent_max_tokens` | Бюджет completion tokens по intent | Настраивается в Admin Console → Orchestrator; снижение ускоряет ответ, но при слишком низком значении возможно `response_truncated_by_max_tokens` |
| `rag_distance_threshold` | Фильтр шумных чанков | **0.6** в текущей конфигурации. Было 1.35 — при этом пороге RAG возвращал нерелевантные материалы (например, уроки Claude Code по запросу «Fine-Tuning»), и LLM либо отказывалась отвечать на фоне ложных источников, либо давала общее определение из своих знаний. Уменьшение до 0.6 отсекло шум и улучшило точность source attribution. |
| `course_boost_enabled` | Приоритизировать чанки, совпадающие по `course_id` | `true` — для учебных вопросов мягко повышает ранг материалов текущего курса, не отсекая общие материалы |
| `course_boost_factor` | Сила курсового буста | 0.15 по умолчанию; 0 — отключить влияние `course_id` на ранжирование |
| `system_prompt` + `output_rules` | Размер prompt | Избыточный текст увеличивает prompt tokens и latency |
| `max_history_messages` | Длина истории в prompt | Меньше сообщений — меньше токенов |

### 🎓 11.2. AI Config — default instructions backfill

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

## 🗄️ 12. Retention и архивы

### 📜 12.1. Политика хранения

AI Curator разделяет эксплуатационные данные на две категории с разными сроками хранения:

| Категория | Таблицы | Срок хранения | Переменная |
|-----------|---------|---------------|------------|
| **Hot logs** | `chat_requests`, `chat_logs`, `analytics_events`, `audit_logs`, `llm_calls` | 30 дней | `HOT_RETENTION_DAYS` |
| **LLM traces** | `llm_call_traces` (полные prompt/response) | 7 дней | `TRACE_RETENTION_DAYS` |

По достижении срока записи архивируются в `ARCHIVE_DIR` как gzip-сжатые JSON Lines и удаляются из PostgreSQL.

### 🗃️ 12.2. Архивы

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

### ⏰ 12.3. Расписание cleanup

Cleanup запускается фоновой задачей `main.py::_retention_cleanup_loop()`:

- Интервал: раз в 24 часа.
- При ошибке: повторная попытка через 1 час.
- Задача не должна падать основное приложение.
- Сам cleanup фиксируется в `audit_logs` как `action=retention_cleanup`, `resource_type=system`.

### 📤 12.4. Экспорт логов

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

---

## 🧪 13. Тестирование

Подробный контракт тестирования — в `docs/TESTING_CONTRACT.md`. Краткая сводка:

| Маркер | Что проверяет | Команда |
|--------|--------------|---------|
| `unit` | Быстрые тесты без внешних сетевых вызовов | `pytest tests/ -m unit -q` |
| `integration` | Интеграции с LMS, RAG, Chroma, chat pipeline | `pytest tests/ -m integration -q` |
| `expensive` | Дорогие LLM-тесты (зарезервированы) | `pytest tests/ -m expensive -q` |
| (все) | Полный прогон | `pytest tests/ -q` |

### 🧰 13.1. Требования к окружению

- `TEST_DATABASE_URL` — отдельная PostgreSQL, например `ai_curator_test`. Никогда не должна совпадать с `DATABASE_URL`.
- `PYTEST_ALLOW_PROD_DB=false` в production и `.env.example`.
- `CHROMA_TEST_COLLECTION_NAME` — изолированная тестовая коллекция (по умолчанию `ai_curator_kb_test`).

### ▶️ 13.2. Запуск внутри backend-контейнера

```bash
docker compose exec ai-curator-backend pytest tests/ -m unit -q
docker compose exec ai-curator-backend pytest tests/ -m integration -q
docker compose exec ai-curator-backend pytest tests/ -q
```

### 🛡️ 13.3. Защита от случайного использования боевой БД

Если `TEST_DATABASE_URL` не задана и `PYTEST_ALLOW_PROD_DB` не `true`, pytest завершается с ошибкой:

```
TEST_DATABASE_URL is not configured. Set TEST_DATABASE_URL to a dedicated test database,
or set PYTEST_ALLOW_PROD_DB=true to intentionally use the production database for tests.
```

---

## 🔗 14. Связанные документы

- [🎛️ `docs/ADMIN_GUIDE.md`](ADMIN_GUIDE.md) — руководство администратора по Консоли администратора.

---

## 📝 15. История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-07-30 | 1.0 | Создан документ |
| 2026-07-31 | 1.1 | Добавлены KB workflow, AI Config tuning, Orchestrator Configuration |
| 2026-08-01 | 1.2 | Добавлены Dialog Sessions, Audit Log, execution tracing |
| 2026-08-02 | 1.3 | Добавлен Response Cache; аудит ограничен изменяющими действиями и chat_request |
| 2026-08-03 | 1.4 | Актуализирован раздел latency и NFR/SLO |
| 2026-08-05 | 1.5 | Добавлены retention policy и CSV-экспорт логов |
| 2026-08-05 | 1.6 | Актуализирован раздел Knowledge Base под реальный UI Admin Console; удалены не реализованные в UI функции |
| 2026-08-05 | 1.7 | Полная фактическая проверка: AI и Retrieval, Orchestrator, Analytics, Monitoring, Operational Logs, Dialog Sessions, Audit; исправлены token budgets и нумерация разделов |
| 2026-08-05 | 1.8 | Расставлены эмодзи по контракту `shared/patterns/documentation-emoji-contract.md` для всех H1–H3 заголовков; добавлена обратная ссылка на `ADMIN_GUIDE.md` |
