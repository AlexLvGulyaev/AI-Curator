# AI Curator — Testing Cost Contract

**Версия:** 1.0  
**Дата:** 2026-08-02  
**Статус:** Active

---

## 1. Назначение

Этот документ фиксирует контракт тестирования backend AI Curator:

- какие тесты существуют и как они размечены;
- какое окружение требуется для каждого набора;
- сколько стоят (время, внешние вызовы, токены);
- какие команды запускать в разных ситуациях;
- как избежать загрязнения боевой БД и Chroma тестами.

Контракт является **Source of Truth** для разработчиков, CI/CD и ручных прогонов.

---

## 2. Требования к окружению

| Переменная | Назначение | Пример |
|---|---|---|
| `DATABASE_URL` | Боевая PostgreSQL | `postgresql+asyncpg://ai_curator:PASS@ai-curator-postgres:5432/ai_curator` |
| `TEST_DATABASE_URL` | Отдельная тестовая PostgreSQL | `postgresql+asyncpg://ai_curator:PASS@ai-curator-postgres:5432/ai_curator_test` |
| `CHROMA_HOST` / `CHROMA_PORT` | Chroma HTTP endpoint | `ai-curator-chroma`, `8000` |
| `CHROMA_COLLECTION_NAME` | Продакшен коллекция | `ai_curator_kb` |
| `CHROMA_TEST_COLLECTION_NAME` | Тестовая коллекция | `ai_curator_kb_test` |
| `PYTEST_ALLOW_PROD_DB` | Fallback на боевую БД, если `TEST_DATABASE_URL` не задан | `false` (только `true` в явных fallback-сценариях) |

**Правило безопасности:** `pytest` по умолчанию **не запускается**, если `TEST_DATABASE_URL` не задана. Для явного fallback нужно установить `PYTEST_ALLOW_PROD_DB=true`.

---

## 3. Номенклатура тестов

| Маркер | Что тестирует | Внешние вызовы | Количество (≈) | Время прогона |
|---|---|---|---|---|
| `unit` | Быстрые тесты без сетевых вызовов: health, AI-config, analytics, prompt builder, orchestrator config, audit, KB CRUD без embeddings, execution tracer unit | Нет | 27 | < 30 сек |
| `integration` | Интеграционные тесты с LMS, LLM/RAG-mocks, Chroma embeddings, chat endpoint | LMS API, OpenAI embeddings, Chroma | 28 | 2–5 мин |
| `expensive` | Дорогие тесты, потребляющие значительное количество токенов LLM | OpenAI chat completions | 0 | — |

### 3.1. `unit` — дешёвые тесты

- Не делают сетевых вызовов.
- Используют тестовую БД и тестовую Chroma-коллекцию.
- Подходят для pre-commit и CI на каждый PR.

### 3.2. `integration` — интеграционные тесты

- `test_courses.py`, `test_deadlines.py` — реальные запросы к Moodle API.
- `test_chat.py`, `test_dialog_sessions.py` — сквозные HTTP-сценарии с моками LMS и/или LLM.
- `test_rag.py`, часть `test_kb.py` — создание embeddings в Chroma через OpenAI `text-embedding-3-small`.
- Запускаются на тестовой БД и тестовой Chroma-коллекции.

### 3.3. `expensive` — дорогие LLM-тесты

- В текущей версии зарезервированы на будущее.
- Когда появятся, должны запускаться вручную или по расписанию, но не на каждый PR.

---

## 4. Команды запуска

```bash
# 1. Дешёвые unit-тесты (pre-commit / CI на каждый PR)
pytest tests/ -m unit -q

# 2. Интеграционные тесты (требуют LMS, OpenAI key, Chroma)
pytest tests/ -m integration -q

# 3. Дорогие тесты (зарезервированы)
pytest tests/ -m expensive -q

# 4. Все тесты (явный полный прогон)
pytest tests/ -q

# 5. Исключить интеграционные и дорогие (эквивалент unit)
pytest tests/ -m "not integration and not expensive" -q
```

---

## 5. Стоимость и цель каждого набора

| Набор | Цель | Ресурсы | Когда запускать |
|---|---|---|---|
| `unit` | Быстрая проверка регрессий в API, моделях, сервисах | Только тестовая БД | Каждый коммит, CI |
| `integration` | Проверка интеграций с LMS, RAG, chat pipeline | LMS, OpenAI embeddings, Chroma | Перед deploy, ночной CI |
| `expensive` | Проверка качества ответов реального LLM | OpenAI chat tokens | Ручно, по расписанию |

---

## 6. Изоляция тестов

### 6.1. PostgreSQL

- Тесты используют БД, указанную в `TEST_DATABASE_URL`.
- `tests/conftest.py` создаёт БД `ai_curator_test`, если её нет, и применяет Alembic-миграции.
- Каждый тест выполняется в транзакции с откатом, что обеспечивает изоляцию.
- Фоновые задачи приложения (`main.py` lifespan, retention cleanup) переопределяются на тестовый engine/session factory.

### 6.2. Chroma

- Тесты пишут в коллекцию `CHROMA_TEST_COLLECTION_NAME` (`ai_curator_kb_test` по умолчанию).
- Перед сессией тестов тестовая коллекция удаляется и пересоздаётся.
- Продакшен коллекция `ai_curator_kb` не затрагивается.

### 6.3. Защита от случайного использования prod

- Если `TEST_DATABASE_URL` не задана и `PYTEST_ALLOW_PROD_DB` не `true`, `pytest` падает с сообщением об ошибке.
- `PYTEST_ALLOW_PROD_DB` должна быть `false` в `.env.example` и `.env` production.

---

## 7. CI/CD рекомендации

| Стадия | Команда | Условие успеха |
|---|---|---|
| Lint / type check | `ruff check src/`, `mypy src/` (если настроены) | Zero errors |
| Unit tests | `pytest tests/ -m unit -q` | Все passed |
| Integration tests | `pytest tests/ -m integration -q` | Все passed |
| Pre-deploy | Полный прогон `pytest tests/ -q` | Все passed |

---

## 8. Smoke-testing политика

- **Smoke-тесты не пишут в боевую БД.** Все автоматические тесты работают на `ai_curator_test`.
- **Smoke-тесты не пишут в продакшен Chroma.** Все embeddings-создания идут в `ai_curator_kb_test`.
- Перед запуском любых тестов `pytest` валидирует `TEST_DATABASE_URL`.
- Ручные E2E-сценарии на продакшене — это не pytest smoke-тесты; они документируются отдельно.

---

## 9. Изменение контракта

Любое добавление/удаление маркера, изменение команд или стоимости требует обновления этого документа.
