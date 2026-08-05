# API_CONTRACT.md — AI Curator Backend

**Проект:** ai-curator  
**Версия:** 1.5
**Дата:** 2026-08-05
**Статус:** Актуален: chat, admin KB/AI/orchestrator, analytics, reports, audit, logs, demo mode, CSV export

---

## 1. Общие соглашения

- Базовый URL production: `https://curator-api.alex-n8n.site`
- Версионированный API: `/api/v1`
- Публичные health endpoints: `/health/*`
- Все ответы в формате `application/json`
- Авторизация студентов в текущей версии не реализована (`/api/v1/me/progress` возвращает данные тестового пользователя `student_demo`).
- Примеры запросов и curl-скриптов — в [`docs/examples/`](examples/).

---

## 2. Публичные health endpoints

### 2.1. `GET /health`

Базовая проверка жизни backend.

**Ответ 200 OK:**

```json
{
  "status": "ok",
  "service": "ai-curator-backend"
}
```

---

### 2.2. `GET /health/db`

Проверка подключения к PostgreSQL.

**Ответ 200 OK:**

```json
{
  "status": "ok",
  "database": "connected",
  "result": 1
}
```

**Ответ 200 OK при ошибке подключения:**

```json
{
  "status": "error",
  "database": "disconnected",
  "detail": "..."
}
```

---

### 2.3. `GET /health/lms`

Проверка подключения к LMS через LMS Adapter.

**Ответ 200 OK:**

```json
{
  "status": "ok",
  "lms": "connected",
  "response_time_ms": 108.63
}
```

**Ответ 200 OK при недоступности LMS:**

```json
{
  "status": "error",
  "lms": "disconnected",
  "detail": "...",
  "response_time_ms": 15000.0
}
```

---

### 2.4. `GET /health/chroma`

Проверка подключения к векторному хранилищу Chroma.

**Ответ 200 OK:**

```json
{
  "status": "ok",
  "chroma": "connected",
  "heartbeat": 1785357296085464040
}
```

**Ответ 200 OK при недоступности Chroma:**

```json
{
  "status": "error",
  "chroma": "disconnected",
  "detail": "..."
}
```

---

## 3. API v1

### 3.1. `GET /api/v1/health`

Версионированный аналог `GET /health`.

**Ответ 200 OK:**

```json
{
  "status": "ok",
  "service": "ai-curator-backend"
}
```

---

### 3.2. `GET /api/v1/courses`

Возвращает список курсов из LMS.

**Ответ 200 OK:**

```json
[
  {
    "id": 1,
    "shortname": "AI Curator",
    "fullname": "AI Curator Demo LMS",
    "displayname": "AI Curator Demo LMS",
    "summary": null,
    "visible": true,
    "start_date": null,
    "end_date": null,
    "url": "https://lms.alex-n8n.site/course/view.php?id=1"
  },
  {
    "id": 3,
    "shortname": "claude-code-express",
    "fullname": "Claude Code: от знакомства до автоматизации",
    "displayname": "Claude Code: от знакомства до автоматизации",
    "summary": null,
    "visible": true,
    "start_date": "2026-07-29T18:39:21Z",
    "end_date": "2027-07-29T18:39:21Z",
    "url": "https://lms.alex-n8n.site/course/view.php?id=3"
  }
]
```

**Возможные ошибки:**

- `502 Bad Gateway` — не удалось получить данные из LMS.

---

### 3.3. `GET /api/v1/courses/{course_id}/contents`

Возвращает структуру курса: секции и модули (страницы, задания, форумы и т.д.).

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `course_id` | int | Идентификатор курса в LMS |

**Ответ 200 OK:**

```json
[
  {
    "id": 9,
    "instance_id": 1,
    "name": "CC01. Установка и первый запуск Claude Code",
    "modname": "page",
    "section_id": 7,
    "section_name": "Модуль 1. Знакомство с Claude Code",
    "section_number": 1,
    "visible": true,
    "url": "https://lms.alex-n8n.site/mod/page/view.php?id=9",
    "contents": [...],
    "description": null
  }
]
```

---

### 3.4. `GET /api/v1/courses/{course_id}/deadlines`

Возвращает дедлайны заданий (assignments) для указанного курса.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `course_id` | int | Идентификатор курса в LMS |

**Ответ 200 OK:**

```json
[
  {
    "id": 10,
    "course_id": 3,
    "module_id": 24,
    "instance_id": 10,
    "name": "ДЗ: Установка и первый запуск Claude Code",
    "modname": "assign",
    "due_date": "2026-08-01T18:49:57Z",
    "allow_submissions_from": null,
    "cutoff_date": null,
    "url": "https://lms.alex-n8n.site/mod/assign/view.php?id=24"
  }
]
```

Для демо-курса `course_id=3` возвращается 9 заданий.

**Возможные ошибки:**

- `502 Bad Gateway` — не удалось получить данные из LMS.

---

### 3.5. `GET /api/v1/me/progress`

Возвращает прогресс текущего студента в демо-курсе.

**Важно:** в Sprint 3.2 авторизация не реализована. Текущий пользователь зафиксирован как `student_demo` (Moodle user id = 3) в курсе `course_id = 3`.

**Ответ 200 OK:**

```json
{
  "user_id": 3,
  "course_id": 3,
  "user_fullname": "Student Demo",
  "completion_status": "in_progress",
  "grade_items": [
    {
      "id": 12,
      "name": "ДЗ: Установка и первый запуск Claude Code",
      "item_type": "mod",
      "item_module": "assign",
      "item_instance": 10,
      "category_id": 2,
      "cmid": 24,
      "grade_raw": null,
      "grade_max": 100,
      "grade_min": 0,
      "grade_formatted": "-",
      "feedback": null,
      "submitted_at": null,
      "graded_at": null
    }
  ],
  "overall_grade": null,
  "overall_grade_max": null,
  "overall_grade_formatted": "-"
}
```

**Возможные ошибки:**

- `502 Bad Gateway` — не удалось получить данные из LMS.

---

### 3.6. `POST /api/v1/admin/kb/documents`

Загрузка нового документа в Knowledge Base. Поддерживаются `text/markdown`, `text/plain` и `application/pdf`.

**Параметры формы (multipart/form-data):**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `title` | string | ✅ | Название документа |
| `document_type` | string | — | `lecture` (по умолчанию), `methodical`, `faq`, `instruction`, `glossary`, `example`, `external` |
| `course_id` | int | — | Привязка к курсу LMS |
| `module_id` | int | — | Привязка к модулю курса |
| `topic_id` | int | — | Привязка к теме |
| `language` | string | — | Код языка, по умолчанию `ru` |
| `description` | string | — | Описание документа |
| `source_url` | string | — | URL источника |
| `file` | file | ✅ | Файл документа |

**Ответ 201 Created:**

```json
{
  "id": 31,
  "title": "Claude Code: быстрый старт",
  "document_type": "lecture",
  "course_id": 3,
  "module_id": 1,
  "topic_id": null,
  "language": "ru",
  "description": null,
  "source_url": null,
  "is_published": false,
  "status": "pending",
  "last_error": null,
  "active_version_id": 32,
  "versions": [
    {
      "id": 32,
      "version_number": 1,
      "storage_path": "31/v1_... .md",
      "original_filename": "quick-start.md",
      "file_size": 1234,
      "mime_type": "text/markdown",
      "status": "pending",
      "chunk_count": null,
      "is_active": true,
      "raw_storage_path": "31/v1_raw_... .md",
      "cleaned_storage_path": null,
      "sha256": "a1b2c3...",
      "indexed_at": null,
      "embedding_model": null,
      "git_commit_hash": null,
      "git_blob_hash": null,
      "git_author": null,
      "git_commit_message": null,
      "git_committed_at": null,
      "created_at": "2026-07-29T21:38:00Z",
      "updated_at": "2026-07-29T21:38:00Z"
    }
  ],
  "created_at": "2026-07-29T21:38:00Z",
  "updated_at": "2026-07-29T21:38:00Z"
}
```

**Возможные ошибки:**

- `415 Unsupported Media Type` — MIME-тип файла не поддерживается.

---

### 3.7. `GET /api/v1/admin/kb/documents`

Список документов Knowledge Base с фильтрами и пагинацией.

**Параметры запроса:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `course_id` | int | Фильтр по курсу |
| `module_id` | int | Фильтр по модулю |
| `is_published` | bool | Фильтр по статусу публикации |
| `limit` | int | Лимит, по умолчанию 100, макс. 500 |
| `offset` | int | Смещение, по умолчанию 0 |

**Ответ 200 OK:** массив объектов `KbDocumentOut`.

---

### 3.8. `GET /api/v1/admin/kb/documents/{document_id}`

Карточка одного документа с версиями и фрагментами.

**Ответ 200 OK:** объект `KbDocumentOut`.

**Возможные ошибки:**

- `404 Not Found` — документ не найден.

---

### 3.9. `PUT /api/v1/admin/kb/documents/{document_id}`

Обновление метаданных документа.

**Тело запроса (JSON):**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `title` | string | Название |
| `document_type` | string | Тип документа |
| `course_id` | int | Курс |
| `module_id` | int | Модуль |
| `topic_id` | int | Тема |
| `language` | string | Язык |
| `description` | string | Описание |
| `source_url` | string | URL источника |

**Ответ 200 OK:** обновлённый объект `KbDocumentOut`.

---

### 3.10. `DELETE /api/v1/admin/kb/documents/{document_id}`

Мягкое удаление (архивирование) документа и всех его версий.

**Ответ 204 No Content**.

---

### 3.11. `POST /api/v1/admin/kb/documents/{document_id}/versions`

Загрузка новой версии существующего документа.

**Параметры формы (multipart/form-data):**

| Параметр | Тип | Обязательный | Описание |
|----------|-----|--------------|----------|
| `file` | file | ✅ | Новый файл версии |

**Ответ 200 OK:** обновлённый объект `KbDocumentOut`.

---

### 3.12. `POST /api/v1/admin/kb/documents/{document_id}/publish`

Публикация или снятие с публикации документа.

**Параметры запроса:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `publish` | bool | `true` (по умолчанию) — опубликовать, `false` — снять с публикации |

**Ответ 200 OK:** обновлённый объект `KbDocumentOut`.

---

### 3.13. `POST /api/v1/admin/kb/documents/{document_id}/process`

Запускает обработку активной версии документа: извлечение текста, разбиение на фрагменты, генерацию embeddings и индексацию в Chroma.

**Ответ 200 OK:** обновлённый объект `KbDocumentOut` со статусом `indexed`.

**Возможные ошибки:**

- `404 Not Found` — документ не найден.
- `400 Bad Request` — нет активной версии или ошибка обработки (подробности в `last_error`).

---

### 3.14. `GET /api/v1/admin/kb/status`

Агрегированный статус Knowledge Base.

**Ответ 200 OK:**

```json
{
  "total_documents": 10,
  "published_documents": 0,
  "draft_documents": 0,
  "total_versions": 10,
  "active_versions": 10,
  "total_chunks": 0,
  "indexed_chunks": 0,
  "last_updated": "2026-07-29T21:38:00Z"
}
```

---

### 3.15. `GET /api/v1/admin/kb/documents/{document_id}/detail`

Полный операционный bundle документа: метаданные, активная версия, чанки, lifecycle timeline и технические параметры выполнения. Используется центральной панелью консоли KB Documents.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |

**Ответ 200 OK:** объект `KbDocumentDetailOut`.

**Возможные ошибки:**

- `404 Not Found` — документ не найден.

---

### 3.16. `GET /api/v1/admin/kb/documents/{document_id}/versions/{version_id}/text`

Возвращает preview RAW или cleaned текста версии документа.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |
| `version_id` | int | Идентификатор версии |

**Параметры запроса:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `stage` | string | `raw` или `cleaned` (по умолчанию `cleaned`) |
| `full` | bool | `true` — вернуть полный текст в пределах лимита 10 МБ; `false` — первые 262 144 символа |

**Ответ 200 OK:** объект `KbVersionTextOut`.

**Возможные ошибки:**

- `404 Not Found` — документ или версия не найдены.
- `400 Bad Request` — некорректное значение `stage` или ошибка чтения файла.

---

### 3.17. `POST /api/v1/admin/kb/documents/{document_id}/versions/{version_id}/text`

Сохранение отредактированного очищенного (cleaned) текста версии с опциональной переиндексацией.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |
| `version_id` | int | Идентификатор версии |

**Параметры запроса:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `stage` | string | Только `cleaned` (по умолчанию) |
| `reindex` | bool | `true` (по умолчанию) — пересчитать чанки и проиндексировать; `false` — только сохранить текст |

**Тело запроса (JSON):**

```json
{
  "text": "# Claude Code: быстрый старт\n\nУстановите пакет..."
}
```

**Ответ 200 OK:** обновлённый объект `KbDocumentOut`.

**Возможные ошибки:**

- `400 Bad Request` — `stage` не равен `cleaned`, либо версия заархивирована, либо документ не найден.
- `404 Not Found` — документ или версия не найдены.

---

### 3.18. `GET /api/v1/admin/kb/documents/{document_id}/versions/{version_id}/chunks`

Возвращает чанки (фрагменты) конкретной версии с `content_preview`.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |
| `version_id` | int | Идентификатор версии |

**Ответ 200 OK:** массив объектов `KbDocumentChunkOut`.

**Возможные ошибки:**

- `404 Not Found` — документ или версия не найдены.

---

### 3.19. `GET /api/v1/admin/kb/documents/{document_id}/timeline`

Возвращает lifecycle timeline документа: загрузка, обработка, индексация, публикация, ошибки и др.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |

**Параметры запроса:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `limit` | int | Лимит событий, по умолчанию 100, макс. 500 |

**Ответ 200 OK:** массив объектов `KbDocumentEventOut`.

**Возможные ошибки:**

- `404 Not Found` — документ не найден.

---

### 3.20. `POST /api/v1/admin/kb/documents/{document_id}/versions/{version_id}/activate`

Делает указанную версию активной без переиндексации. Используется в таблице версий операционной консоли.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |
| `version_id` | int | Идентификатор версии |

**Ответ 200 OK:** обновлённый объект `KbDocumentOut`.

**Возможные ошибки:**

- `404 Not Found` — документ или версия не найдены.
- `400 Bad Request` — ошибка активации.

---

### 3.21. `POST /api/v1/admin/kb/documents/{document_id}/versions/{version_id}/reindex`

Активирует указанную версию и запускает её переиндексацию.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |
| `version_id` | int | Идентификатор версии |

**Ответ 200 OK:** обновлённый объект `KbDocumentOut`.

**Возможные ошибки:**

- `404 Not Found` — документ или версия не найдены.
- `400 Bad Request` — ошибка переиндексации.

---

### 3.22. `POST /api/v1/admin/kb/documents/{document_id}/reindex`

Переиндексирует активную версию документа. Эквивалент нажатия **Переиндексировать** в toolbar.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `document_id` | int | Идентификатор документа |

**Ответ 200 OK:** обновлённый объект `KbDocumentOut`.

**Возможные ошибки:**

- `404 Not Found` — документ не найден.
- `400 Bad Request` — нет активной версии или ошибка переиндексации.

---

### 3.23. `POST /api/v1/admin/kb/reindex-all`

Массовая переиндексация всех опубликованных документов. Используется при смене embedding model или массовом обновлении контента.

**Ответ 200 OK:**

```json
{
  "processed": 18,
  "failed": 1,
  "total": 19
}
```

---

### 3.24. `POST /api/v1/rag/search`

Семантический поиск по индексированным фрагментам Knowledge Base.

**Тело запроса (JSON):**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `query` | string | Поисковый запрос |
| `document_id` | int | Ограничить поиск одним документом (опционально) |
| `course_id` | int | Фильтр по курсу (опционально) |
| `module_id` | int | Фильтр по модулю (опционально) |
| `topic_id` | int | Фильтр по теме (опционально) |
| `k` | int | Количество результатов, по умолчанию 5, макс. 20 |

**Ответ 200 OK:**

```json
{
  "query": "установка Claude Code npm",
  "results": [
    {
      "chunk_id": "41:0",
      "content": "Для установки Claude Code выполните команду npm install -g @anthropic-ai/claude-code...",
      "metadata": {
        "document_id": 31,
        "version_id": 41,
        "chunk_index": 0,
        "status": "indexed"
      },
      "distance": 0.123
    }
  ],
  "total": 1
}
```

---

### 3.25. `POST /api/v1/chat`

Публичный чат со студентами. Backend классифицирует запрос, получает данные из LMS и/или Knowledge Base, формирует промпт, вызывает LLM и возвращает ответ с источниками.

**Заголовки:**

| Заголовок | Описание |
|-----------|----------|
| `X-Demo-Token` | Токен демо-сессии. **Обязателен** в production, когда `DEMO_ENABLED=true`. В dev/test без `DEMO_ENABLED` токен не требуется. |

**Тело запроса (JSON):**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `message` | string | Вопрос студента |
| `role` | string | Демо-роль студента (опционально) |
| `difficulty` | string | Уровень подготовки: `beginner`, `intermediate`, `advanced` |
| `course_id` | int | ID курса в LMS (опционально) |
| `session_id` | string | ID сессии диалога (опционально) |
| `history` | array | Последние сообщения диалога (`{role, content}`) |

**Ответ 200 OK:**

```json
{
  "answer": "## Дедлайны по курсу\n\n1. **ДЗ: Установка...** — 1 августа 2026 г.\n...",
  "sources": [
    {"type": "lms", "title": "ДЗ: Установка и первый запуск Claude Code", "url": "https://lms.alex-n8n.site/mod/assign/view.php?id=24", "module": "Модуль 1"},
    {"type": "kb", "title": "Методичка: Установка Claude Code", "document_type": "methodical", "document_id": 12, "chunk_index": 3}
  ],
  "intent": "organizational",
  "model": "gpt-4o-mini-2024-07-18",
  "latency_ms": 1234.56,
  "session_id": "...",
  "cache_hit": false,
  "error": null,
  "log_id": 12345,
  "demo_mode": false
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `answer` | string | Текст ответа AI |
| `sources` | array[ChatSource] | Источники ответа (LMS / Knowledge Base) |
| `intent` | string | Классифицированный интент |
| `model` | string \| null | Модель LLM |
| `latency_ms` | float \| null | Задержка в миллисекундах |
| `session_id` | string \| null | ID диалоговой сессии |
| `cache_hit` | bool | Ответ получен из кэша |
| `error` | string \| null | Ошибка, если произошла |
| `log_id` | int \| null | ID записи в `chat_logs`; используется Web UI для отправки feedback |
| `demo_mode` | bool | Признак demo-запроса. При `true` ответ формируется с уменьшенным `max_tokens` и повышенным TTL кэша. |

#### Схема `ChatSource`

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | string | Тип источника: `kb` (Knowledge Base) или `lms` (LMS) |
| `title` | string | Название источника |
| `url` | string \| null | Прямая ссылка (только для LMS) |
| `document_type` | string \| null | Тип KB-документа: `lecture`, `methodical`, `faq`, `instruction`, `glossary`, `example`, `external` |
| `module` | string \| null | Название модуля/темы (обычно для LMS) |
| `topic` | string \| null | Название темы (зарезервировано) |
| `section` | string \| null | Название секции (зарезервировано) |
| `document_id` | int \| null | ID KB-документа |
| `chunk_index` | int \| null | Индекс чанка внутри документа |

**Кэширование:**

- Ответы кэшируются по ключу `SHA256(message | role | difficulty | course_id | intent)`.
- `cache_hit: true` означает, что ответ был возвращён из кэша без вызова LMS/RAG/LLM.
- Кэш инвалидируется при изменении KB, AI-config, retrieval tuning и orchestrator config.

---

### 3.26. `POST /api/v1/chat/{log_id}/feedback`

Студент отправляет оценку полезности конкретного ответа AI. Оценка записывается в поле `feedback_score` таблицы `chat_logs`.

**Параметры пути:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `log_id` | int | ID записи в `chat_logs` (поле `log_id` из ответа `POST /api/v1/chat`) |

**Тело запроса (JSON):**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `score` | int | Оценка от 1 до 10 |

**Ответ 204 No Content** — оценка успешно сохранена.

**Возможные ошибки:**

- `404 Not Found` — запись `chat_logs` с указанным `log_id` не найдена.
- `422 Unprocessable Entity` — `score` вне диапазона 1–10 (валидация Pydantic).

**Аудит:** при каждом успешном сохранении в `audit_logs` создаётся запись `action="chat_feedback"`, `resource_type="chat_log"`, `resource_id="<log_id>"` с `score` и предыдущей оценкой.

---

### 3.27. `POST /api/v1/demo/start`

Создаёт новую демо-сессию для публичного Web UI. Возвращает токен, который необходимо передавать в заголовке `X-Demo-Token` на каждый `POST /api/v1/chat`.

**Тело запроса (JSON):**

| Поле | Тип | Описание |
|------|-----|----------|
| `session_id` | string | Опциональный business session_id |

**Ответ 200 OK:**

```json
{
  "token": "f5a3efee30bc453bbfa96604af7dce54",
  "session_id": null,
  "requests_limit": 20,
  "requests_remaining": 20,
  "rate_limit_per_minute": 12,
  "expires_at": "2026-08-05T04:10:34.488823+00:00"
}
```

**Возможные ошибки:**

- `403 Forbidden` — demo-режим не включён (`DEMO_ENABLED=false`).
- `429 Too Many Requests` — превышен лимит сессий с одного IP-адреса.

---

### 3.28. `GET /api/v1/demo/status`

Возвращает текущее состояние демо-сессии: использованные и оставшиеся запросы, время истечения.

**Заголовки:**

| Заголовок | Описание |
|-----------|----------|
| `X-Demo-Token` | Токен демо-сессии |

**Ответ 200 OK:**

```json
{
  "token": "f5a3efee30bc453bbfa96604af7dce54",
  "session_id": null,
  "requests_used": 3,
  "requests_limit": 20,
  "requests_remaining": 17,
  "expires_at": "2026-08-05T04:10:34.488823+00:00",
  "is_active": true
}
```

**Возможные ошибки:**

- `401 Unauthorized` — отсутствует или истёкший `X-Demo-Token`.
- `404 Not Found` — сессия не найдена.

---

## 4. Административные endpoints (`/api/v1/admin/*`)

### 4.1. AI Configuration

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/ai-config` | Активная конфигурация AI |
| `GET` | `/api/v1/admin/ai-config/history` | История версий конфигурации |
| `POST` | `/api/v1/admin/ai-config` | Создать новую версию конфигурации |
| `POST` | `/api/v1/admin/ai-config/{id}/activate` | Активировать версию |

**Поля конфигурации (`POST /api/v1/admin/ai-config`):**

| Поле | Тип | Обязательное | Описание |
|------|-----|--------------|----------|
| `name` | string | ✅ | Название версии |
| `system_prompt` | string | ✅ | System prompt |
| `model` | string | — | Модель LLM, по умолчанию `gpt-4o-mini` |
| `temperature` | float | — | 0.0–2.0, по умолчанию 0.3 |
| `max_tokens` | int | — | 1–4096, по умолчанию 1024 |
| `top_k_retrieval` | int | — | 1–20, по умолчанию 5 |
| `rag_distance_threshold` | float | — | 0.0–10.0, по умолчанию 1.35 |
| `beginner_instructions` | string | — | Инструкции для уровня beginner |
| `advanced_instructions` | string | — | Инструкции для уровня advanced |
| `few_shot_examples` | string | — | Few-shot примеры |
| `output_rules` | string | — | Правила оформления ответа |
| `refusal_answer_text` | string | — | Текст стандартного отказа |
| `max_history_messages` | int | — | 0–50, по умолчанию 6 |

### 4.2. Analytics

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/analytics/dashboard` | Ключевые метрики |
| `GET` | `/api/v1/admin/analytics/topics` | Распределение по темам |
| `GET` | `/api/v1/admin/analytics/unanswered` | Вопросы без ответа |
| `GET` | `/api/v1/admin/analytics/feedback` | Распределение оценок |
| `GET` | `/api/v1/admin/analytics/events` | Сырые аналитические события |

### 4.3. Monitoring

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/monitoring/status` | Состояние компонентов с задержками, AI-активностью, KB-статусом и последними ошибками |
| `GET` | `/api/v1/admin/monitoring/health` | Агрегированный health check |
| `GET` | `/api/v1/admin/monitoring/errors` | Последние ошибки и предупреждения обработки запросов |

**Параметры `GET /api/v1/admin/monitoring/errors`:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `limit` | int | Лимит, по умолчанию 10, max 100 |

**Каноническая модель `RecentError`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `source` | string | Источник: `chat_log`, `execution_session`, `execution_step` |
| `session_id` | string \| null | Business session ID |
| `intent` | string \| null | Intent запроса |
| `stage_name` | string \| null | Стадия pipeline (для `execution_step`) |
| `status` | string | `error` / `warning` |
| `error` | string | Текст ошибки или предупреждения |
| `execution_session_id` | int \| null | ID execution-сессии (для `execution_session` / `execution_step`) |
| `created_at` | string | ISO timestamp |

Ошибки собираются из трёх источников:
1. `chat_logs.error` — ошибки LLM и exception в `process()`.
2. `execution_sessions.status IN ('error', 'warning')` — статус всего pipeline.
3. `execution_steps.status IN ('error', 'warning')` — ошибки отдельных стадий (`lms_fetch`, `rag_search` и др.), включая частичные сбои, которые были замаскированы fallback-ответом.

### 4.4. Operational Logs

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/operational-logs` | Список operational log entries (запросы студентов) |
| `GET` | `/api/v1/admin/operational-logs/{id}` | Деталь operational log entry |
| `POST` | `/api/v1/admin/operational-logs/export` | CSV-экспорт operational logs по текущим фильтрам |

**Параметры фильтрации `GET /api/v1/admin/operational-logs` и `POST /api/v1/admin/operational-logs/export`:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `session_id` | string | Фильтр по session_id |
| `role` | string | Фильтр по роли |
| `course_id` | int | Фильтр по курсу |
| `intent` | string | Фильтр по intent |
| `status` | string | `ok`, `error`, `pending` |
| `has_error` | bool | Только записи с ошибкой |
| `date_from` | string | ISO date YYYY-MM-DD |
| `date_to` | string | ISO date YYYY-MM-DD |
| `limit` | int | Лимит, по умолчанию 20, max 100 |
| `offset` | int | Смещение |

**Каноническая модель `OperationalLogSummary`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID записи |
| `session_id` | string | ID сессии |
| `role` | string | Роль пользователя |
| `course_id` | int | ID курса |
| `difficulty` | string | Уровень сложности |
| `intent` | string | Классифицированный intent |
| `message_preview` | string | Превью сообщения (до 200 символов) |
| `status` | string | `ok` / `error` / `pending` |
| `latency_ms` | float | Задержка ответа |
| `total_tokens` | int | Токены |
| `llm_model` | string | Модель LLM |
| `cache_hit` | bool | Ответ получен из кэша |
| `created_at` | string | ISO timestamp |

**Каноническая модель `OperationalLogDetail`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID записи |
| `session_id` | string | ID сессии |
| `role` | string | Роль |
| `course_id` | int | ID курса |
| `difficulty` | string | Уровень сложности |
| `intent` | string | Intent |
| `message` | string | Полный текст запроса |
| `lms_calls` | array | Вызовы LMS |
| `rag_filters` | object | Фильтры RAG |
| `created_at` | string | ISO timestamp |
| `status` | string | Статус |
| `answer` | string | Ответ AI |
| `sources` | array | Источники ответа |
| `llm_model` | string | Модель LLM |
| `latency_ms` | float | Задержка |
| `total_tokens` | int | Токены |
| `feedback_score` | int | Оценка полезности |
| `cache_hit` | bool | Ответ получен из кэша |
| `error` | string | Ошибка |
| `llm_calls` | array | Метаданные вызовов LLM + trace preview |
| `analytics_events` | array | Связанные analytics events |

### 4.5. Dialog Sessions

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/dialog-sessions` | Список канонических диалоговых сессий из `chat_sessions` |
| `GET` | `/api/v1/admin/dialog-sessions/{session_id}` | Деталь сессии: turns, execution timeline, budget, JSON snapshot |
| `POST` | `/api/v1/admin/dialog-sessions/export` | CSV-экспорт списка диалоговых сессий |

**Параметры фильтрации `GET /api/v1/admin/dialog-sessions` и `POST /api/v1/admin/dialog-sessions/export`:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `hours` | int | Фильтр по сессиям, обновлённым за последние N часов (1–720) |
| `mode` | string | Source mode: `text`, `lms`, `rag`, `mixed` |
| `active_only` | bool | Только активные сессии |
| `search` | string | Поиск по `session_id` или `role` |
| `limit` | int | Лимит, по умолчанию 20, max 100 |
| `offset` | int | Смещение |

**Каноническая модель `DialogSessionSummary`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID канонической сессии (PK) |
| `session_id` | string | Business session ID |
| `message_count` | int | Количество запросов в сессии |
| `first_message_at` | string | ISO timestamp первого сообщения |
| `last_message_at` | string | ISO timestamp последнего сообщения |
| `role` | string | Роль пользователя |
| `course_id` | int | ID курса |
| `difficulty` | string | Уровень сложности |
| `mode` | string | Source mode: `text`, `lms`, `rag`, `mixed` |
| `is_active` | bool | Активна ли сессия |
| `status` | string | `ok` / `error` / `pending` |

**Каноническая модель `DialogSessionDetail`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID канонической сессии |
| `session_id` | string | Business session ID |
| `user_id` | int \| null | ID пользователя |
| `role` | string | Роль |
| `course_id` | int | ID курса |
| `difficulty` | string | Сложность |
| `mode` | string | Source mode |
| `is_active` | bool | Активность |
| `message_count` | int | Всего запросов |
| `first_message_at` | string | ISO timestamp |
| `last_message_at` | string | ISO timestamp |
| `turns` | array[DialogTurn] | Пары запрос/ответ |
| `execution_sessions` | array[ExecutionSession] | Трассировки execution pipeline |
| `budget` | object | Снапшот активной AI-конфигурации (`model`, `max_tokens`, `temperature`) |
| `memory_source` | string | Значение `PostgreSQL` |
| `limit` | int | Лимит turns |
| `offset` | int | Смещение turns |

**Каноническая модель `DialogTurn`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `request_id` | int | ID запроса |
| `log_id` | int | ID chat_log |
| `role` | string | Роль пользователя |
| `course_id` | int | ID курса |
| `difficulty` | string | Сложность |
| `intent` | string | Intent |
| `user_message` | string | Сообщение пользователя |
| `assistant_answer` | string | Ответ AI |
| `sources` | array | Источники ответа |
| `status` | string | `ok` / `error` / `pending` |
| `llm_model` | string | Модель |
| `latency_ms` | float | Задержка |
| `total_tokens` | int | Токены |
| `feedback_score` | int | Оценка полезности |
| `cache_hit` | bool | Ответ получен из кэша |
| `error` | string | Ошибка |
| `rag_filters` | object | Фильтры RAG |
| `lms_calls` | array | Вызовы LMS |
| `created_at` | string | ISO timestamp |

**Каноническая модель `ExecutionSession`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID execution-сессии |
| `request_id` | int \| null | ID связанного chat-запроса |
| `route` | string \| null | Маршрут |
| `status` | string | `started`, `ok`, `error` |
| `client_ip` | string \| null | IP клиента |
| `provider_key` | string \| null | Ключ провайдера LLM |
| `model_name` | string \| null | Модель LLM |
| `duration_ms` | int \| null | Длительность в ms |
| `started_at` | string | ISO timestamp начала |
| `finished_at` | string \| null | ISO timestamp окончания |
| `execution_metadata` | object | JSON-метаданные: timings, route, short_circuit, cache_hit |
| `steps` | array[ExecutionStep] | Этапы pipeline |

**Каноническая модель `ExecutionStep`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID шага |
| `stage_name` | string | `intent_classify`, `cache_hit`, `lms_fetch`, `rag_search`, `context_build`, `llm_call`, `answer_validate`, `source_attach`, `response_save` |
| `step_order` | int | Порядковый номер |
| `status` | string | `ok`, `error`, `warning` |
| `duration_ms` | int \| null | Длительность в ms |
| `started_at` | string \| null | ISO timestamp |
| `finished_at` | string \| null | ISO timestamp |
| `step_metadata` | object | JSON-метаданные шага |

### 4.6. Audit

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/audit` | Журнал аудита с фильтрами |
| `GET` | `/api/v1/admin/audit/{id}` | Деталь audit-записи |
| `POST` | `/api/v1/admin/audit/export` | CSV-экспорт журнала аудита по текущим фильтрам |

**Примечание:** export endpoints являются read-only и доступны как с полным admin-токеном, так и с demo-токеном Admin Console. Это осознанное решение: демо-пользователь может просматривать и выгружать логи, но не может выполнять mutating-операции.

В аудит записываются только **изменяющие административные действия** и публичные `chat_request`. Read-only просмотры (`GET /api/v1/admin/audit`, `GET /api/v1/admin/dialog-sessions`, `GET /api/v1/admin/operational-logs`, `GET /api/v1/admin/monitoring/*`, `GET /api/v1/admin/analytics/*`, `GET /api/v1/admin/kb/documents/*/detail`, `GET /api/v1/admin/kb/documents/*/versions/*/text`, `GET /api/v1/admin/kb/documents/*/versions/*/chunks`) намеренно **не аудитируются**, чтобы журнал не порождал сам себя.

Кроме административных действий, в аудит записываются публичные `chat_request` (каждый запрос в `POST /api/v1/chat`) с `resource_id == session_id`, `user_id == role`, `user_name == "student"` и реальным `ip_address`.

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `action` | string | Действие |
| `resource_type` | string | Тип ресурса |
| `user_id` | string | ID или имя пользователя (сопоставляется с `user_id` и `user_name`) |
| `date_from` | string | ISO date YYYY-MM-DD |
| `date_to` | string | ISO date YYYY-MM-DD |
| `limit` | int | Лимит, по умолчанию 100 |
| `offset` | int | Смещение |

**Ответ `GET /api/v1/admin/audit`:**

```json
{
  "items": [AuditLogEntry],
  "total": 42,
  "limit": 100,
  "offset": 0
}
```

**Каноническая модель `AuditLogEntry`:**

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | ID записи |
| `user_id` | string \| null | ID пользователя |
| `user_name` | string \| null | Имя пользователя |
| `user_role` | string \| null | Роль |
| `action` | string | Действие |
| `resource_type` | string | Тип ресурса |
| `resource_id` | string \| null | ID ресурса |
| `ip_address` | string \| null | IP-адрес клиента |
| `details` | object | JSON-метаданные |
| `created_at` | string | ISO timestamp |
| `updated_at` | string \| null | ISO timestamp |

### 4.7. Reports (Business Reports / Quality Reports)

Управленческая сводка для анализа качества ответов и покрытия Knowledge Base. Все endpoints read-only и не пишут в `audit_logs`.

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/reports/quality` | Качество ответов: answered rate, error rate, fallback rate, cache hit rate, средняя оценка, RAG coverage |
| `GET` | `/api/v1/admin/reports/unanswered` | Пагинированный список вопросов без ответа |
| `GET` | `/api/v1/admin/reports/kb-gaps` | study/mixed запросы, отвеченные без источников KB/RAG |
| `GET` | `/api/v1/admin/reports/popular-topics` | Распределение запросов по intent |
| `GET` | `/api/v1/admin/reports/kb-coverage` | Покрытие KB по курсам и типам документов |
| `GET` | `/api/v1/admin/reports/expansion-candidates` | Кандидаты на расширение KB (intent с наибольшим числом гэпов) |
| `GET` | `/api/v1/admin/reports/export` | CSV-экспорт unanswered + KB gaps |

**Общие параметры фильтрации:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `date_from` | string | ISO date YYYY-MM-DD |
| `date_to` | string | ISO date YYYY-MM-DD |
| `course_id` | int | ID курса |

**Пагинированные endpoints** (`/unanswered`, `/kb-gaps`) дополнительно принимают `intent`, `limit`, `offset`.

**Ответ `GET /api/v1/admin/reports/quality`:**

```json
{
  "total_requests": 1250,
  "answered_count": 1180,
  "answered_rate": 94.4,
  "error_count": 12,
  "error_rate": 0.96,
  "fallback_count": 18,
  "fallback_rate": 1.44,
  "cache_hit_count": 320,
  "cache_hit_rate": 25.6,
  "average_feedback_score": 8.2,
  "rag_eligible_count": 420,
  "rag_covered_count": 380,
  "rag_coverage_rate": 90.48
}
```

**Ответ `GET /api/v1/admin/reports/unanswered` и `/kb-gaps`:**

```json
{
  "items": [
    {
      "request_id": 123,
      "session_id": "...",
      "message": "Как работает рекурсия?",
      "intent": "study",
      "course_id": 3,
      "role": "active_student",
      "difficulty": "beginner",
      "created_at": "2026-08-04T12:00:00+00:00",
      "answer": null,
      "sources": null,
      "feedback_score": null,
      "latency_ms": null,
      "cache_hit": false,
      "error": null
    }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

**Ответ `GET /api/v1/admin/reports/popular-topics`:**

```json
[
  {"intent": "study", "count": 640},
  {"intent": "deadline", "count": 210},
  {"intent": "organizational", "count": 180},
  {"intent": "mixed", "count": 90},
  {"intent": "out_of_scope", "count": 45}
]
```

**Ответ `GET /api/v1/admin/reports/kb-coverage`:**

```json
{
  "total_documents": 25,
  "documents_by_type": [
    {"document_type": "lecture", "count": 12},
    {"document_type": "faq", "count": 8},
    {"document_type": "instruction", "count": 5}
  ],
  "coverage_by_course": [
    {
      "course_id": 3,
      "total_documents": 18,
      "published_documents": 15,
      "chunk_count": 142
    }
  ]
}
```

**Ответ `GET /api/v1/admin/reports/expansion-candidates`:**

```json
[
  {
    "intent": "study",
    "gap_count": 38,
    "recommendation": "Добавить или расширить материалы Knowledge Base по этой теме."
  }
]
```

**`GET /api/v1/admin/reports/export`:**

- Параметр `section` — `unanswered`, `kb-gaps` или `all` (по умолчанию).
- Возвращает `text/csv; charset=utf-8` с BOM (`utf-8-sig`) для корректного открытия в Excel.
- Колонки: `report_section`, `request_id`, `session_id`, `created_at`, `role`, `course_id`, `intent`, `difficulty`, `message`, `answer_preview`, `feedback_score`, `latency_ms`, `cache_hit`, `error`.

### 4.8. Авторизация

Административные endpoints защищены Bearer-токеном. Используются два токена:

| Роль | Переменная | Доступ |
|------|------------|--------|
| `admin` | `ADMIN_CONSOLE_TOKEN` | Полный доступ ко всем endpoints (read + write). |
| `demo` | `ADMIN_CONSOLE_DEMO_TOKEN` | Только read-only endpoints (`GET`, CSV export). Любая мутация (`POST`, `PUT`, `DELETE`) возвращает `403 Forbidden`. |

Если `ADMIN_CONSOLE_TOKEN` не задан, авторизация отключена (например, в тестах). Web UI и публичный чат не требуют авторизации.

**Пример ошибки для demo-пользователя при попытке мутации:**

```json
{
  "detail": "Demo access is read-only"
}
```

### 4.9. Orchestrator Configuration

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/orchestrator/config` | Текущая конфигурация оркестратора |
| `PUT` | `/api/v1/admin/orchestrator/config` | Обновить конфигурацию оркестратора |

**Поля конфигурации (`PUT /api/v1/admin/orchestrator/config`):**

| Поле | Тип | Описание |
|------|-----|----------|
| `intent_rules` | object | Правила интент-классификации: keywords и условия для каждого intent |
| `default_intent` | string | Intent по умолчанию, когда ни одно правило не сработало |
| `intent_source_map` | object | Маппинг intent → `{lms, rag, strict_course}` |
| `non_course_starters` | array[string] | Слова, которые не считаются названиями курсов при экстракции |
| `max_lms_contents` | int | Максимальное число элементов LMS contents в prompt |
| `max_lms_deadlines` | int | Максимальное число дедлайнов в prompt |
| `intent_max_tokens` | object | Маппинг intent-ключа → max output tokens |
| `fallback_messages` | object | Сообщения для `no_lms_data`, `no_rag_context`, `out_of_scope_course` |

**Пример ответа `GET /api/v1/admin/orchestrator/config`:**

```json
{
  "id": 1,
  "intent_rules": {
    "deadline": {
      "keywords": ["дедлайн", "дедлайны", "срок", "сдача", "когда", "до когда", "когда сдать"],
      "priority": 1
    },
    "progress": {
      "keywords": ["прошёл", "завершил", "сдал", "выполнил", "мой прогресс", "мои результаты"],
      "priority": 2
    },
    "study": {
      "keywords": ["лекция", "методичка", "объясни", "расскажи", "что такое", "как работает"],
      "priority": 3
    },
    "mixed": {
      "conditions": [
        {"and": ["is_org", "is_study"]},
        {"and": ["is_org", "has_keyword", ["модуль", "модули", "структура курса"]]}
      ],
      "priority": 4
    },
    "organizational": {
      "conditions": [{"and": ["is_org"]}],
      "priority": 5
    }
  },
  "default_intent": "study",
  "intent_source_map": {
    "deadline": {"lms": true, "rag": false, "strict_course": true},
    "progress": {"lms": true, "rag": false, "strict_course": true},
    "organizational": {"lms": true, "rag": false, "strict_course": true},
    "study": {"lms": false, "rag": true, "strict_course": false},
    "mixed": {"lms": true, "rag": true, "strict_course": true}
  },
  "non_course_starters": ["когда", "сколько", "какой", "объясни", "расскажи"],
  "max_lms_contents": 12,
  "max_lms_deadlines": 5,
  "intent_max_tokens": {
    "organizational": 500,
    "study_beginner": 650,
    "mixed": 800,
    "default": 750
  },
  "fallback_messages": {
    "no_lms_data": "В курсе пока нет опубликованных заданий с дедлайнами. Если вы ожидаете увидеть задание, обратитесь к преподавателю.",
    "no_rag_context": "У меня недостаточно данных, чтобы точно ответить. Обратитесь к преподавателю.",
    "out_of_scope_course": "У меня нет данных о курсе «{course}» для вашей учётной записи. Обратитесь к преподавателю."
  },
  "created_at": "2026-07-31T12:00:00Z",
  "updated_at": "2026-07-31T12:00:00Z"
}
```

При отсутствии строки в таблице backend автоматически создаёт конфигурацию с defaults, идентичными текущему хардкоду, чтобы обеспечить graceful degradation.

---

## 5. Канонические модели данных

### 5.1. `Course`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор курса в LMS |
| `shortname` | string | Короткое имя курса |
| `fullname` | string | Полное имя курса |
| `displayname` | string \| null | Отображаемое имя |
| `summary` | string \| null | Описание курса |
| `visible` | bool | Видимость курса |
| `start_date` | ISO-8601 \| null | Дата начала |
| `end_date` | ISO-8601 \| null | Дата окончания |
| `url` | string \| null | Прямая ссылка на курс в LMS |

### 5.2. `Deadline`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор задания в LMS |
| `course_id` | int | Идентификатор курса |
| `module_id` | int | Course module id (cmid) |
| `instance_id` | int | Instance id задания |
| `name` | string | Название задания |
| `modname` | string | Тип модуля, обычно `assign` |
| `due_date` | ISO-8601 \| null | Дедлайн сдачи |
| `allow_submissions_from` | ISO-8601 \| null | Начало приёма сдач |
| `cutoff_date` | ISO-8601 \| null | Жёсткий дедлайн |
| `url` | string \| null | Ссылка на задание в LMS |

### 5.3. `UserCourseProgress`

| Поле | Тип | Описание |
|------|-----|----------|
| `user_id` | int | Идентификатор пользователя |
| `course_id` | int | Идентификатор курса |
| `user_fullname` | string \| null | Полное имя пользователя |
| `completion_status` | string \| null | Статус прохождения |
| `grade_items` | list[GradeItem] | Оценочные элементы |
| `overall_grade` | float \| null | Общий балл |
| `overall_grade_max` | float \| null | Максимальный общий балл |
| `overall_grade_formatted` | string \| null | Отформатированная итоговая оценка |

### 5.4. `GradeItem`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор элемента оценки |
| `name` | string \| null | Название |
| `item_type` | string | Тип (`mod`, `course`, `category`) |
| `item_module` | string \| null | Модуль (`assign`, `quiz`, ...) |
| `item_instance` | int \| null | Instance id |
| `category_id` | int \| null | Идентификатор категории оценок |
| `cmid` | int \| null | Course module id |
| `grade_raw` | float \| null | Сырой балл |
| `grade_max` | float \| null | Максимальный балл |
| `grade_min` | float \| null | Минимальный балл |
| `grade_formatted` | string \| null | Отформатированный балл |
| `feedback` | string \| null | Обратная связь |
| `submitted_at` | ISO-8601 \| null | Время сдачи |
| `graded_at` | ISO-8601 \| null | Время оценивания |

### 5.5. `KbDocumentOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор документа |
| `title` | string | Название |
| `document_type` | string | Тип документа |
| `course_id` | int \| null | **Advisory retrieval-фильтр**: идентификатор курса, к которому материал желательно привязать. Не является foreign key из LMS; отсутствие значения не делает материал недействительным. |
| `module_id` | int \| null | **Advisory retrieval-фильтр**: идентификатор модуля. |
| `topic_id` | int \| null | **Advisory retrieval-фильтр**: идентификатор темы. |
| `difficulty` | string | Уровень сложности |
| `language` | string | Язык |
| `description` | string \| null | Описание |
| `source_url` | string \| null | URL источника |
| `is_published` | bool | Опубликован ли документ |
| `status` | string | Статус (`draft`, `pending`, `processing`, `indexed`, `error`, `archived`) |
| `last_error` | string \| null | Последняя ошибка обработки |
| `active_version_id` | int \| null | ID активной версии |
| `versions` | list[KbDocumentVersionOut] | Версии документа |
| `created_at` | ISO-8601 | Дата создания |
| `updated_at` | ISO-8601 | Дата обновления |

### 5.6. `KbDocumentVersionOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор версии |
| `version_number` | int | Номер версии |
| `storage_path` | string | Путь к файлу в хранилище |
| `original_filename` | string | Исходное имя файла |
| `file_size` | int \| null | Размер файла в байтах |
| `mime_type` | string \| null | MIME-тип |
| `status` | string | Статус версии |
| `chunk_count` | int \| null | Количество фрагментов |
| `is_active` | bool | Активна ли версия |
| `raw_storage_path` | string \| null | Путь к RAW-оригиналу |
| `cleaned_storage_path` | string \| null | Путь к очищенной копии |
| `sha256` | string \| null | SHA-256 файла |
| `indexed_at` | ISO-8601 \| null | Время последней индексации |
| `embedding_model` | string \| null | Модель embeddings |
| `git_commit_hash` | string \| null | Git commit hash версии |
| `git_blob_hash` | string \| null | Git blob hash версии |
| `git_author` | string \| null | Автор commit'а |
| `git_commit_message` | string \| null | Сообщение commit'а |
| `git_committed_at` | ISO-8601 \| null | Время commit'а |
| `created_at` | ISO-8601 | Дата создания |
| `updated_at` | ISO-8601 | Дата обновления |

### 5.7. `KbDocumentChunkOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор чанка |
| `chunk_index` | int | Порядковый номер чанка |
| `char_start` | int \| null | Символ начала в оригинале |
| `char_end` | int \| null | Символ конца в оригинале |
| `token_count` | int \| null | Количество токенов |
| `content_preview` | string \| null | Первые символы текста чанка |
| `status` | string | Статус чанка |
| `created_at` | ISO-8601 \| null | Дата создания |

### 5.8. `KbDocumentEventOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор события |
| `document_id` | int | Идентификатор документа |
| `version_id` | int \| null | Идентификатор версии |
| `event_type` | string | Тип события (`upload`, `preprocess_start`, `preprocess_done`, `preprocess_error`, `index_start`, `index_done`, `index_error`, `reindex_start`, `reindex_done`, `reindex_error`, `publish`, `unpublish`, `metadata_update`, `version_activate`, `delete`, `error` и др.) |
| `status` | string | `success`, `error`, `pending` |
| `message` | string \| null | Описание / ошибка |
| `details` | object \| null | JSON с техническими подробностями |
| `created_at` | ISO-8601 | Время события |
| `started_at` | ISO-8601 \| null | Время начала операции |
| `finished_at` | ISO-8601 \| null | Время окончания операции |
| `duration_ms` | int \| null | Длительность в миллисекундах |

### 5.9. `KbVersionTextOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `version_id` | int | Идентификатор версии |
| `version_number` | int | Номер версии |
| `stage` | string | `raw` или `cleaned` |
| `original_filename` | string | Исходное имя файла |
| `mime_type` | string \| null | MIME-тип |
| `total_length` | int | Полная длина текста |
| `preview_length` | int | Длина возвращённого preview |
| `preview` | string | Текст (или его начало) |

### 5.10. `KbDocumentExecutionOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `provider` | string \| null | Провайдер embeddings / LLM |
| `model` | string \| null | Модель embeddings |
| `backend` | string \| null | Backend retrieval (например, `chroma`) |
| `sha256` | string \| null | SHA-256 активной версии |
| `indexed_at` | ISO-8601 \| null | Время индексации |
| `raw_size` | int \| null | Размер RAW-файла |
| `cleaned_size` | int \| null | Размер cleaned-файла |
| `postgres_status` | string \| null | Статус документа в PostgreSQL |

### 5.11. `KbDocumentDetailOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `document` | KbDocumentOut | Метаданные документа и все версии |
| `active_version` | KbDocumentVersionOut \| null | Активная версия |
| `chunks` | list[KbDocumentChunkOut] | Чанки активной версии |
| `timeline` | list[KbDocumentEventOut] | Lifecycle timeline |
| `execution` | KbDocumentExecutionOut | Технические параметры выполнения |

### 5.12. `KbReindexAllOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `processed` | int | Количество успешно обработанных |
| `failed` | int | Количество неудач |
| `total` | int | Общее количество |

---

## 6. Пользовательские интерфейсы

### 6.1. Web UI AI Curator

- URL: `https://curator.alex-n8n.site`.
- Стек: React + Vite + Tailwind CSS.
- Гостевой вход с выбором одной из трёх демо-ролей: `active_student`, `late_student`, `new_student`.
- Сессия хранится в `localStorage`.
- Web UI использует `POST /api/v1/chat` для диалога с LLM.
- Markdown-ответы рендерятся безопасно (sanitized).
- История диалога сохраняется в `localStorage`.

### 6.2. Admin Console AI Curator

- URL: `https://curator-admin.alex-n8n.site`.
- Стек: React + Vite + Tailwind CSS (тёмная административная тема).
- Аутентификация по Bearer-токену из переменной окружения `ADMIN_CONSOLE_TOKEN`.
- Возможности:
  - панель состояния системы;
  - управление Knowledge Base через трёхпанельную операционную консоль: загрузка, версии, переиндексация, lifecycle, preview текста и чанков, редактирование cleaned-текста;
  - AI Configuration (версионирование, активация);
  - аналитика запросов и оценок;
  - operational logs (запросы студентов, LLM calls, analytics events);
  - журнал аудита.

## 7. Ограничения и допущения

1. **Авторизация студентов:** не реализована. Web UI использует гостевые демо-роли.
2. **Авторизация администраторов:** административные endpoints защищены статическим Bearer-токеном.
3. **Read-only LMS:** LMS Adapter использует только read-only Web Service functions и проверяет их по белому списку.
4. **Chroma health check:** использует прямой HTTP-запрос к `/api/v2/heartbeat`, потому что `chromadb==1.5.9` клиент совместим с сервером Chroma latest (v2 API).
5. **Прогресс:** `student_demo` и курс `id=3` зафиксированы в коде до появления аутентификации.
6. **Knowledge Base:** обработка документов (`/process`) синхронная.
7. **База данных:** используется `NullPool` для asyncpg, чтобы избежать состояния гонки в тестах через ASGITransport.

---

## 8. История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-07-29 | 1.0 | Начальный API-контракт: LMS, Knowledge Base, RAG, chat |
| 2026-07-30 | 1.1 | Добавлены admin endpoints: AI-config, analytics, monitoring, audit |
| 2026-07-31 | 1.2 | Добавлены KB operational console, orchestrator config, уточнены KB метаданные |
| 2026-08-01 | 1.3 | Добавлены operational logs, dialog sessions, execution tracing, расширенный audit |
| 2026-08-02 | 1.4 | Добавлен Response Cache; аудит ограничен изменяющими действиями и chat_request |
| 2026-08-05 | 1.5 | Добавлены business reports, demo mode Web UI, feedback endpoint, CSV export logs |
