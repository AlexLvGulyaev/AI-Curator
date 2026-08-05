# Отчёт о соответствии ТЗ

**Проект:** AI Curator — AI-ассистент для образовательной платформы  
**Дата среза:** 2026-08-04  
**Источник ТЗ:** исходное техническое задание проекта.

Документ описывает **фактическую реализацию** в репозитории и БД PostgreSQL (контейнер `ai-curator-postgres`, БД `ai_curator`). Не содержит маркетинговых формулировок и планов.

---

## 1. Цель проекта

### Формулировка из ТЗ

> Создание AI-ассистента, который поможет студентам ориентироваться в материалах курса, отвечать на организационные и учебные вопросы, а также рекомендовать дополнительные ресурсы с учётом уровня подготовки.

### Соответствие

| Требование ТЗ | Реализация (факт на 2026-08-04) | Статус |
|---------------|----------------------------------|--------|
| Помощь студентам в материалах курса | Web UI: чат, история диалога, источники, переключатель сложности | **Выполнено** |
| Организационные и учебные вопросы | Orchestrator классифицирует интенты: `organizational`, `deadline`, `progress`, `study`, `mixed`, `out_of_scope`, `error`, `refusal` | **Выполнено** |
| Рекомендации с учётом уровня подготовки | `difficulty` (`beginner`/`advanced`) влияет на `PromptBuilder`; `beginner_instructions` / `advanced_instructions` в `ai_configs` | **Выполнено** |
| Платформа: OpenAI API + LangChain/LlamaIndex (техн. ТЗ) | FastAPI + LangChain + Chroma + PostgreSQL; мультимодельность: OpenAI primary + GigaChat fallback | **Выполнено и расширено** |
| Векторная БД | Chroma в Docker Compose; embeddings OpenAI `text-embedding-3-small` | **Выполнено** |
| Формат сдачи: Jupyter Notebook или Streamlit | Заменён на публичный Web UI + Admin Console на React + VPS + HTTPS | **Частично** — см. §10 |
| API-имитация LMS через JSON/CSV заглушку | Заменена на read-only интеграцию с реальным Moodle LMS | **Частично** — см. §10 |
| Пример дашборда аналитики | Admin Console Analytics Dashboard с фильтрами, графиками, latency histogram, источниками, CSV export | **Выполнено** |

---

## 2. Бизнес-задачи

| Требование ТЗ | Факт в системе | Статус |
|---------------|----------------|--------|
| Снижение нагрузки на преподавателей и техподдержку | Автоматические ответы на типовые организационные и учебные вопросы; fallback-сообщения при недостатке данных | **Выполнено** |
| Повышение вовлечённости и завершаемости курсов | Персонализированные рекомендации, прогресс из LMS, уровень сложности | **Выполнено** |
| Персонализация учебных траекторий | `course_id`, `module_id`, `topic_id` в метаданных KB; `strict_course` routing для LMS-интентов | **Выполнено** |
| Сбор аналитики по частым вопросам | `chat_requests` + `chat_logs` + `analytics_events`; Admin Console Analytics с распределением по интентам, источникам, latency, ошибкам | **Выполнено** |

---

## 3. Архитектура промптов и сценариев

### 3.1. Роль AI-ассистента

Системный промпт хранится в `ai_configs.system_prompt`. Активная конфигурация в БД (`id=65`, модель `gpt-4o-mini`, `active_provider=openai`).

Структура промпта собирается в `src/services/prompt_builder.py`:

| Часть | Источник |
|-------|----------|
| System Prompt | `ai_config.system_prompt` — роль, запреты, стиль |
| User Context | `role`, `difficulty`, `course_id` |
| LMS Data | `lms_data` — дедлайны, задания, прогресс |
| RAG Context | `rag_context` — фрагменты KB с `document_id` / `chunk_index` |
| Few-shot | `ai_config.few_shot_examples` |
| Conversation History | `history` (последние N сообщений) |
| Output Rules | `ai_config.output_rules` |

### 3.2. Сценарии ответов

Сценарии реализованы через **Orchestrator** (`src/services/orchestrator.py`):

| Интент | Источники | strict_course | Пример вопроса |
|--------|-----------|---------------|----------------|
| `deadline` | LMS | Да | «Когда сдать задание?» |
| `progress` | LMS | Да | «Какие модули я прошёл?» |
| `organizational` | LMS | Да | «Сколько уроков в курсе?» |
| `study` | RAG/KB | Нет | «Объясни, что такое промпт-инжиниринг» |
| `mixed` | LMS + RAG | Да | «Что повторить перед заданием в пятницу?» |
| `out_of_scope` | fallback | — | Вопрос вне контекста курса |
| `error` | fallback | — | Техническая ошибка pipeline |
| `refusal` | — | — | Запрещённые действия (оценки, дедлайны) |

Конфигурация интентов и маршрутизации управляется через таблицу `orchestrator_configs` (`intent_rules`, `intent_source_map`, `fallback_messages`, `non_course_starters`) и редактируется в Admin Console → Orchestrator Configuration.

### 3.3. Ограничения

| Ограничение ТЗ | Реализация |
|----------------|------------|
| Не выставляет оценки | `AnswerValidator.FORBIDDEN_PATTERNS` и `REFUSAL_REQUEST_PATTERNS` → `refusal` intent |
| Не меняет расписание | Та же refusal-логика + только read-only LMS Adapter |
| Всегда ссылается на источник | Ответы сопровождаются `sources`: LMS-ссылки или KB-чанки |
| Адаптация уровня сложности | `difficulty` → `beginner_instructions` / `advanced_instructions` в `PromptBuilder` |

---

## 4. RAG-пайплайн и база знаний

### 4.1. Индексация

- `src/services/document_processor.py` — загрузка, извлечение текста, chunking через LangChain.
- `src/services/rag_pipeline.py` — embeddings OpenAI + Chroma retrieval.
- `src/services/kb_lifecycle.py` — управление жизненным циклом документа: `DRAFT` → `PROCESSING` → `INDEXED` / `ERROR`.
- Таблицы: `kb_documents`, `kb_document_versions`, `kb_document_chunks`, `kb_document_events`.

### 4.2. Данные из PostgreSQL (срез 2026-08-04)

| Метрика | Значение |
|---------|----------|
| Всего документов | 58 |
| Опубликованных и проиндексированных (`is_published=true AND status='INDEXED'`) | 49 |
| Курсов | 3 (course_id 3, 4 и NULL/тест) |
| Типов документов | 4: `LECTURE`, `INSTRUCTION`, `FAQ`, `ARTICLE` |
| Версий документов | 58 |
| Чанков | 100 |
| Событий | 1057 |

### 4.3. Поиск по метаданным

Retrieval поддерживает фильтры по `course_id`, `module_id`, `topic_id`, `document_type`, `difficulty`, `language`. Параметры retrieval (`top_k`, `distance_threshold`, `course_boost`) управляются через `retrieval_tuning` и `ai_configs`, редактируются в Admin Console.

### 4.4. Few-shot примеры

Хранятся в `ai_configs.few_shot_examples`. Используются при сборке промпта в `PromptBuilder`.

---

## 5. Документирование и аналитика

### 5.1. Документирование

Вместо Google Docs/Notion используется документация в репозитории:

| Документ | Назначение |
|----------|------------|
| `README.md` | Публичное описание проекта |
| `docs/PROJECT_STATE.md` | Состояние, решения, риски |
| `docs/SPEC.md` | Продуктовая спецификация |
| `docs/ARCHITECTURE.md` | Архитектурные решения |
| `docs/IMPLEMENTATION_PLAN.md` | План реализации |
| `docs/API_CONTRACT.md` | API-контракты |
| `docs/PROMPT_ARCHITECTURE.md` | Структура промптов |
| `docs/OPERATIONS.md` | Эксплуатация |
| `docs/ADMIN_CONSOLE.md` | Описание Admin Console |
| `docs/E2E_TEST_PLAN.md` | План E2E-тестирования |
| `docs/PRODUCT_E2E_CHECKLIST.md` | Чек-лист ручных E2E-сценариев |
| `docs/TESTING_CONTRACT.md` | Правила работы с тестовой и production БД |

### 5.2. Логирование и аналитика

Операционные таблицы:

| Таблица | Записей (2026-08-04) | Назначение |
|---------|----------------------|------------|
| `chat_requests` | 141 | Запросы студентов, интент, роль, курс |
| `chat_logs` | 138 | Ответы, источники, latency, ошибки |
| `chat_sessions` | 49 | Диалоговые сессии |
| `llm_calls` | 43 | Вызовы LLM |
| `llm_call_traces` | есть | Трейсы LLM-вызовов |
| `analytics_events` | 101 | Аналитические события |
| `audit_logs` | 779 | Журнал аудита |
| `execution_sessions` | есть | Сессии выполнения |
| `execution_steps` | есть | Этапы выполнения |
| `request_logs` | есть | HTTP-логи |

### 5.3. Распределение интентов

| intent | Количество |
|--------|------------|
| study | 42 |
| deadline | 36 |
| progress | 24 |
| out_of_scope | 19 |
| organizational | 16 |
| error | 3 |
| mixed | 1 |

### 5.4. Analytics Dashboard (Sprint E1)

Реализован в `src/api/v1/admin/analytics.py` + `admin-console/src/components/Analytics.jsx`:

- фильтры по дате и `course_id`;
- KPI: total requests, answers, latency, % answered, unanswered, errors;
- распределение по темам/интентам;
- latency histogram + p50/p95/p99;
- источники ответов: LMS, RAG/KB, оба, кэш, fallback, error;
- список вопросов без ответа;
- CSV export (`/api/v1/admin/analytics/export`).

---

## 6. Техническая реализация

### 6.1. Стек

| Компонент | Реализация |
|-----------|------------|
| Backend | FastAPI, Python 3.12 |
| Frontend | React 19, Vite, Tailwind CSS |
| LLM Provider | **OpenAI primary** (`gpt-4o-mini`) + **GigaChat fallback** (`GigaChat-Max`) |
| Embeddings | OpenAI `text-embedding-3-small` |
| RAG библиотека | LangChain внутри Backend |
| Векторная БД | Chroma |
| Операционная БД | PostgreSQL 16 |
| LMS | Moodle (read-only интеграция) |
| Контейнеризация | Docker + Docker Compose |
| Reverse Proxy / HTTPS | Traefik + Let's Encrypt |
| Кэширование | ResponseCache (PostgreSQL) |

### 6.2. Мультимодельность и fallback LLM

Реализована в:

- `src/services/llm_adapter.py` — OpenAI-совместимый адаптер;
- `src/services/gigachat_adapter.py` — GigaChat-адаптер;
- `src/models/ai_config.py` — поля `active_provider`, `fallback_provider`, `provider_settings` (JSON);
- `src/services/ai_config.py` — выбор активной конфигурации.

Активная конфигурация в БД:

| Поле | Значение |
|------|----------|
| `id` | 65 |
| `model` | `gpt-4o-mini` |
| `active_provider` | `openai` |
| `fallback_provider` | `gigachat` |
| `temperature` | 0.3 |
| `max_tokens` | 1024 |

### 6.3. LMS Adapter

- `src/adapters/lms_adapter.py` — read-only интеграция с Moodle REST API.
- Получает курсы, дедлайны, задания, прогресс, содержание курса.
- Не содержит RAG-логики, не обращается к LLM, не управляет Knowledge Base.

### 6.4. Сервисы Backend

| Сервис | Файл | Назначение |
|--------|------|------------|
| Orchestrator | `src/services/orchestrator.py` | Классификация, маршрутизация, вызов LLM, валидация |
| Prompt Builder | `src/services/prompt_builder.py` | Сборка промпта |
| Answer Validator | `src/services/answer_validator.py` | Проверка ответа на запреты и качество |
| RAG Pipeline | `src/services/rag_pipeline.py` | Retrieval из Chroma |
| LLM Adapter | `src/services/llm_adapter.py` | Вызов OpenAI |
| GigaChat Adapter | `src/services/gigachat_adapter.py` | Fallback LLM |
| Document Processor | `src/services/document_processor.py` | Обработка документов |
| KB Lifecycle | `src/services/kb_lifecycle.py` | Жизненный цикл документов |
| Logger | `src/services/logger.py` | Логирование, execution tracing |
| Response Cache | `src/services/cache/response_cache.py` | Кэширование ответов |

### 6.5. Admin Console

Панели:

- Dashboard;
- AI & Retrieval Configuration;
- Orchestrator Configuration;
- Knowledge Base Documents;
- Dialog Sessions;
- Operational Logs;
- Audit Log;
- Analytics.

Административные endpoints защищены Bearer-токеном `ADMIN_CONSOLE_TOKEN`.

---

## 7. Дисклеймер по персональным данным

| Требование ТЗ | Реализация |
|---------------|------------|
| Учебный проект | Да, демо-данные и тестовые роли (`active_student`, `late_student`, `new_student`) |
| Тестовые или вымышленные данные | Используются синтетические пользователи в Moodle и демо-роли в Web UI |
| Безопасность | API-ключи в `.env`, не в репозитории; HTTPS; разграничение API; read-only LMS |

---

## 8. Итоговое соответствие ТЗ

| Требование ТЗ | Статус | Пояснение |
|---------------|--------|-----------|
| Цель: AI-ассистент для образовательной платформы | **Выполнено** | Развёрнут публичный сервис с Web UI, Admin Console, LMS-интеграцией |
| Бизнес-задачи: снижение нагрузки, вовлечённость, персонализация, аналитика | **Выполнено** | Реализованы все четыре направления |
| Архитектура промптов и сценариев | **Выполнено** | Orchestrator + Prompt Builder + Answer Validator + конфигурируемые интенты |
| RAG-пайплайн и база знаний | **Выполнено** | KB с индексацией, метаданными, поиском, версионированием |
| Документирование и аналитика | **Выполнено** | Markdown-документация в репозитории + Analytics Dashboard |
| Технические требования: OpenAI + LangChain + векторная БД | **Выполнено и расширено** | OpenAI + Chroma + LangChain + мультимодельность с GigaChat fallback |
| Формат сдачи: Jupyter Notebook / Streamlit | **Не реализовано** | Заменён на полноценный web-сервис — осознанное расширение scope |
| API-имитация LMS через заглушку | **Не реализовано** | Заменена на реальную read-only интеграцию с Moodle |
| Дисклеймер по персональным данным | **Выполнено** | Демо-данные, тестовые роли, безопасное хранение секретов |

---

## 9. Источники данных для отчёта

| Источник | Использование |
|----------|---------------|
| README.md | Публичное описание |
| docs/SPEC.md | Продуктовая спецификация |
| docs/ARCHITECTURE.md | Архитектурные решения |
| src/services/orchestrator.py | Классификация, маршрутизация, источники |
| `src/services/prompt_builder.py` | Структура промпта |
| `src/services/answer_validator.py` | Ограничения и отказы |
| `src/services/rag_pipeline.py` | RAG retrieval |
| `src/adapters/lms_adapter.py` | LMS интеграция |
| `src/models/ai_config.py` | Модель конфигурации AI |
| `src/models/orchestrator_config.py` | Модель конфигурации оркестратора |

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — публичное описание проекта.
- [📋 `docs/SPEC.md`](SPEC.md) — продуктовая спецификация.
- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — архитектурные решения.
- [📝 `docs/PROMPT_ARCHITECTURE.md`](PROMPT_ARCHITECTURE.md) — структура промптов.
- [🔌 `docs/API_CONTRACT.md`](API_CONTRACT.md) — API endpoints и payload.
- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание системы.
| `src/api/v1/admin/analytics.py` | Analytics endpoints |
| `admin-console/src/components/Analytics.jsx` | UI аналитики |
| PostgreSQL `ai_curator` | Счётчики таблиц, распределение интентов, active AI config |
