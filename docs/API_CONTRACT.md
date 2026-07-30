# API_CONTRACT.md — AI Curator Backend

**Проект:** ai-curator  
**Версия:** 1.4  
**Дата:** 2026-07-30  
**Статус:** Актуален для Дня 6

---

## 1. Общие соглашения

- Базовый URL production: `https://curator-api.alex-n8n.site`
- Версионированный API: `/api/v1`
- Публичные health endpoints: `/health/*`
- Все ответы в формате `application/json`
- Авторизация студентов в текущей версии не реализована (`/api/v1/me/progress` возвращает данные тестового пользователя `student_demo`)

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
| `difficulty` | string | — | `beginner` (по умолчанию), `intermediate`, `advanced` |
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
  "difficulty": "beginner",
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
| `difficulty` | string | Уровень сложности |
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

### 3.15. `POST /api/v1/rag/search`

Семантический поиск по индексированным фрагментам Knowledge Base.

**Тело запроса (JSON):**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `query` | string | Поисковый запрос |
| `document_id` | int | Ограничить поиск одним документом (опционально) |
| `course_id` | int | Фильтр по курсу (опционально) |
| `module_id` | int | Фильтр по модулю (опционально) |
| `topic_id` | int | Фильтр по теме (опционально) |
| `difficulty` | string | Фильтр по уровню сложности (опционально) |
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
        "difficulty": "beginner",
        "status": "indexed"
      },
      "distance": 0.123
    }
  ],
  "total": 1
}
```

---

### 3.16. `POST /api/v1/chat`

Публичный чат со студентами. Backend классифицирует запрос, получает данные из LMS и/или Knowledge Base, формирует промпт, вызывает LLM и возвращает ответ с источниками.

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
    {"type": "lms", "title": "ДЗ: Установка и первый запуск Claude Code", "url": "https://lms.alex-n8n.site/mod/assign/view.php?id=24"}
  ],
  "intent": "organizational",
  "model": "gpt-4o-mini-2024-07-18",
  "latency_ms": 1234.56,
  "session_id": "...",
  "error": null
}
```

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
| `GET` | `/api/v1/admin/monitoring/status` | Состояние компонентов с задержками |
| `GET` | `/api/v1/admin/monitoring/health` | Агрегированный health check |

### 4.4. Audit

| Метод | Endpoint | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/admin/audit` | Журнал аудита с фильтрами |

**Параметры фильтрации:**

| Параметр | Тип | Описание |
|----------|-----|----------|
| `action` | string | Действие |
| `resource_type` | string | Тип ресурса |
| `user_id` | string | ID пользователя |
| `limit` | int | Лимит, по умолчанию 100 |
| `offset` | int | Смещение |

### 4.5. Авторизация

Административные endpoints защищены Bearer-токеном из переменной окружения `ADMIN_CONSOLE_TOKEN`, если она задана. Web UI и публичный чат не требуют авторизации.

---

## 5. Канонические модели данных

### 4.1. `Course`

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

### 4.2. `Deadline`

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

### 4.3. `UserCourseProgress`

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

### 4.4. `GradeItem`

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

### 4.5. `KbDocumentOut`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | int | Идентификатор документа |
| `title` | string | Название |
| `document_type` | string | Тип документа |
| `course_id` | int \| null | Курс |
| `module_id` | int \| null | Модуль |
| `topic_id` | int \| null | Тема |
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

### 4.6. `KbDocumentVersionOut`

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
| `created_at` | ISO-8601 | Дата создания |
| `updated_at` | ISO-8601 | Дата обновления |

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
  - управление Knowledge Base (загрузка, версии, обработка, публикация);
  - AI Configuration (версионирование, активация);
  - аналитика запросов и оценок;
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
| 2026-07-29 | 1.0 | Начальный API-контракт для Sprint 3.2: courses, deadlines, progress, health endpoints |
| 2026-07-29 | 1.1 | Добавлен Knowledge Base Admin API: загрузка, версии, публикация, статус |
| 2026-07-29 | 1.2 | Добавлены RAG endpoints: `/process`, `/rag/search` |
| 2026-07-29 | 1.3 | Добавлен раздел Web UI, обновлено допущение по Chroma v2 |
| 2026-07-30 | 1.4 | Добавлен `POST /api/v1/chat`, административные endpoints (AI-config, analytics, monitoring, audit), разделы Web UI и Admin Console, авторизация admin |
| 2026-07-30 | 1.5 | Расширены поля AI Configuration; добавлена структура analytics payload с `timings_ms` |
