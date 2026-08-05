# 🏗️ ARCHITECTURE.md — AI Curator

**Проект:** ai-curator
**Версия:** 2.5
**Дата:** 2026-08-05
**Статус:** Approved

---

## 🎯 1. Архитектурные принципы

AI Curator — самостоятельная подсистема образовательной платформы, развёрнутая на VPS.

Ключевые принципы:

- **Backend AI Curator — единый оркестратор** всех пользовательских и административных сценариев.
- **Два независимых источника данных:**
  - **LMS** — Source of Truth учебного процесса.
  - **Knowledge Base AI Curator** — самостоятельный источник учебных материалов.
- **LangChain используется только внутри Backend** как библиотека для RAG и вызовов LLM.
- **LMS Adapter** — внутренний компонент Backend, изолирующий AI Curator от деталей LMS API.
- **Web UI AI Curator** — отдельный публичный сервис на VPS, доступный по собственному HTTPS.
- **Пользовательские интерфейсы не обращаются напрямую** к LMS, Knowledge Base, векторному индексу или LLM.
- **Векторный индекс** — производное хранилище, восстанавливаемое из документов Knowledge Base.
- **Параметры промптов и retrieval** (system prompt, output rules, few-shot, distance threshold, top-k, course boost и др.) управляются через Admin Console и таблицы `ai_configs` / `retrieval_tuning`, а не захардкожены в коде.
- **Параметры интент-классификации и маршрутизации запросов** (keywords, intent → LMS/RAG/strict_course, token бюджеты по intent, fallback-сообщения, размеры LMS-контекста) управляются через Admin Console и таблицу `orchestrator_configs`, а не захардкожены в коде.

---

## 🌐 2. Context Diagram (C4 Level 1)

```mermaid
flowchart TB
    subgraph "Внешние пользователи"
        Student[Студент]
        Teacher[Преподаватель]
        LMSAdmin[Администратор LMS]
        AICAdmin[Администратор AI Curator]
        Methodist[Методист AI Curator]
    end

    subgraph "AI Curator"
        AIC[AI Curator System]
    end

    subgraph "Внешние системы"
        LMS[LMS System]
        LLM[LLM Provider — OpenAI API]
    end

    Student -->|задаёт вопросы, оценивает ответы| AIC
    AICAdmin -->|управляет KB, AI-конфигурацией, мониторингом| AIC
    Methodist -->|управляет материалами, метаданными, FAQ| AIC
    Teacher -->|управляет курсом, заданиями, оценками| LMS
    LMSAdmin -->|управляет LMS, пользователями, интеграцией| LMS

    AIC -->|читает учебный процесс| LMS
    AIC -->|генерирует ответы| LLM
```

---

## 📦 3. Container Diagram (C4 Level 2)

```mermaid
flowchart TB
    subgraph "Внешние пользователи"
        Student[Студент]
        Teacher[Преподаватель]
        LMSAdmin[Администратор LMS]
        AICAdmin[Администратор / Методист AI Curator]
    end

    subgraph "AI Curator"
        WebUI[Web UI AI Curator]
        AdminConsole[Admin Console AI Curator]
        Backend[Backend AI Curator]
    end

    subgraph "Хранилища AI Curator"
        PostgreSQL[(PostgreSQL — операционная база)]
        Chroma[(Chroma — векторный индекс)]
        DocStore[(Хранилище документов)]
    end

    subgraph "Внешние системы"
        LMS[(LMS)]
        LLM[LLM Provider]
    end

    Student -->|HTTPS| WebUI
    AICAdmin -->|HTTPS| AdminConsole
    Teacher -->|HTTPS| LMS
    LMSAdmin -->|HTTPS| LMS

    WebUI -->|JSON API| Backend
    AdminConsole -->|JSON API| Backend

    Backend -->|LMS API| LMS
    Backend -->|SQL| PostgreSQL
    Backend -->|HTTP/gRPC| Chroma
    Backend -->|read/write| DocStore
    Backend -->|REST| LLM
```

---

## 🧩 4. Component Diagram (C4 Level 3 — Backend)

```mermaid
flowchart TB
    subgraph "Backend AI Curator"
        API[API Layer / Auth & Routing]
        Orchestrator[Orchestrator]
        LMSAdapter[LMS Adapter]
        RAG[RAG Pipeline / LangChain Retrieval]
        PromptBuilder[Prompt Builder]
        LLMAdapter[LLM Adapter / LangChain LLM]
        Validator[Answer Validator]
        Logger[Logging, Analytics & Audit]
    end

    subgraph "Внешние зависимости"
        LMS[(LMS)]
        PostgreSQL[(PostgreSQL)]
        Chroma[(Chroma)]
        DocStore[(Doc Store)]
        LLM[(LLM Provider)]
    end

    API --> Orchestrator
    Orchestrator --> LMSAdapter
    Orchestrator --> RAG
    Orchestrator --> PromptBuilder
    Orchestrator --> LLMAdapter
    Orchestrator --> Validator
    Orchestrator --> Logger

    LMSAdapter --> LMS
    RAG --> Chroma
    RAG --> DocStore
    LLMAdapter --> LLM
    Logger --> PostgreSQL
```

---

## 🛡️ 5. Границы ответственности

### 🏫 5.1. LMS

| Аспект | LMS | AI Curator |
|--------|-----|------------|
| Source of Truth учебного процесса | ✅ | ❌ только read-through |
| Пользователи, роли, группы | ✅ | ❌ только читает разрешённое |
| Курсы, модули, темы | ✅ | ❌ только читает разрешённое |
| Задания, тесты, дедлайны | ✅ | ❌ только читает разрешённое |
| Расписание | ✅ | ❌ не изменяет |
| Оценки, прогресс, статусы | ✅ | ❌ только читает разрешённое |

### 🔗 5.1.1. LMS-KB Linking Contract

LMS и Knowledge Base — **два независимых источника**. AI Curator связывает их не через жёсткие foreign keys, а через **контекст пользователя и семантический поиск**.

| Параметр | Семантика | Ограничение |
|----------|-----------|-------------|
| `course_id`, `module_id`, `topic_id` в LMS | Canonical IDs учебного процесса | Source of Truth для структуры, расписания, дедлайнов, прогресса |
| `course_id`, `module_id`, `topic_id` в KB | **Advisory retrieval-фильтры**, помогающие приоритизировать материалы | Не являются FK, не валидируют истинность содержания |

**Правила контракта:**

1. **KB не знает о структуре LMS напрямую.** Методист может загрузить лекцию с `course_id=3`, с `course_id=5` или без `course_id`. KB остаётся валидным источником содержания в любом случае.
2. **LMS не валидирует KB.** Отсутствие курса в LMS не делает KB-материал ложным. Ложным его делает только отсутствие релевантного содержания или несоответствие фактов.
3. **Orchestrator отвечает за объединение контекста.** Он узнаёт курсы студента из LMS и передаёт их в RAG как **мягкий приоритет** (boost), а не как hard-фильтр.
4. **Для organizational/progress/deadline-вопросов** LMS-данные являются единственным допустимым источником. KB в этих сценариях может не использоваться.
5. **Для study-вопросов** релевантность определяется семантическим поиском. Совпадение `course_id` повышает ранг чанка, но не является обязательным условием попадания в контекст.

**Зачем так, а не FK:**

- Методисты могут готовить материалы до появления курса в LMS.
- Один и тот же материал (например, FAQ по Claude Code или методичка по промпт-инжинирингу) может быть полезен в нескольких курсах.
- LLM сохраняет роль «склеивающего слоя» между независимыми источниками, вместо того чтобы система превращалась в SQL-JOIN с векторами.

### 📚 5.2. Knowledge Base AI Curator

Knowledge Base — самостоятельная продуктовая сущность AI Curator, не являющаяся частью LMS.

| Компонент | Роль | Source of Truth |
|-----------|------|-----------------|
| Исходные документы (лекции, методички, FAQ) | ✅ Хранилище документов | ✅ Knowledge Base |
| Метаданные документов | ✅ PostgreSQL | ✅ Knowledge Base |
| Версии и история изменений | ✅ PostgreSQL | ✅ Knowledge Base |
| Векторный индекс (Chroma) | ❌ Производное хранилище | ❌ |

### 🧩 5.3. Backend AI Curator

Backend отвечает за:

- приём и авторизацию запросов;
- классификацию запроса;
- получение данных из LMS через LMS Adapter;
- retrieval по Knowledge Base через LangChain;
- сборку промпта;
- вызов LLM через LangChain;
- проверку и оформление ответа;
- логирование, аналитику, аудит;
- административное API для Knowledge Base, AI-конфигурации и конфигурации оркестратора.

---

## 🔌 6. LMS Adapter

LMS Adapter — внутренний компонент Backend.

**Ответственность:**

- аутентификация и авторизация в LMS API;
- выполнение вызовов к LMS API;
- преобразование ответов LMS во внутренние модели Backend;
- нормализация курсов, модулей, заданий, сроков и прогресса;
- обработка ошибок и недоступности LMS;
- гарантия read-only доступа.

**Ограничения:**

- не содержит RAG-логики;
- не обращается к LLM;
- не управляет Knowledge Base.

```mermaid
flowchart LR
    subgraph "Backend"
        Core[Backend Core]
        Adapter[LMS Adapter]
    end

    subgraph "LMS"
        API[LMS API]
        DB[(LMS DB)]
    end

    Core -->|запрос канонической модели| Adapter
    Adapter -->|LMS API вызовы| API
    API -->|учебные данные| DB
    DB -->|Raw LMS JSON| API
    API -->|Raw LMS JSON| Adapter
    Adapter -->|Canonical Domain Model| Core
```

---

## 📚 7. Knowledge Base и RAG Pipeline

### 📚 7.1. Состав Knowledge Base

Минимальный состав:

- лекции;
- методические материалы;
- FAQ.

Дополнительно допускается:

- инструкции;
- глоссарии;
- примеры решений;
- справочные материалы;
- рекомендованные внешние ресурсы;
- пояснения преподавателей;
- материалы для разных уровней подготовки.

### 🏷️ 7.2. Метаданные материала

- идентификатор;
- название;
- тип материала;
- курс (course_id);
- модуль (module_id);
- тема (topic_id);
- уровень сложности;
- язык;
- версия;
- статус публикации;
- дата добавления;
- дата обновления;
- ссылка или идентификатор исходного документа.

### 🔍 7.3. RAG Pipeline внутри Backend

```mermaid
flowchart LR
    Query[Вопрос студента] --> Backend[Backend / Orchestrator]

    subgraph "RAG Pipeline"
        Backend --> Normalize[Нормализация вопроса]
        Normalize --> Filters[Формирование фильтров]
        Filters --> Embed[LangChain Embeddings]
        Embed --> Chroma[Chroma: semantic + metadata filters]
        Chroma --> Rank[Отбор фрагментов]
        Rank --> Context[Сборка RAG-контекста]
    end

    Context --> Backend
    Backend --> Prompt[Prompt Builder]
    Prompt --> LLMAdapter[LLM Adapter / LangChain LLM]
    LLMAdapter --> LLM[LLM Provider]
    LLM --> LLMAdapter
    LLMAdapter --> Validator[Answer Validator]
    Validator --> Answer[Ответ + источники]
```

RAG Pipeline отвечает только за retrieval, reranking и подготовку RAG-контекста. RAG Pipeline не обращается к LLM напрямую. Единственный вызов модели выполняется через LLM Adapter после сборки промпта в Prompt Builder.

---

## ⏱️ 8. Runtime Sequence — пользовательский запрос

```mermaid
sequenceDiagram
    participant Student as Студент
    participant WebUI as Web UI
    participant API as API Layer
    participant Orchestrator as Orchestrator
    participant LMSAdapter as LMS Adapter
    participant LMS as LMS
    participant RAG as RAG
    participant Chroma as Chroma
    participant Prompt as Prompt Builder
    participant LLMAdapter as LLM Adapter
    participant LLM as LLM Provider
    participant Logger as Logger
    participant DB as PostgreSQL

    Student->>WebUI: Вводит вопрос
    WebUI->>API: POST /api/v1/chat
    API->>Orchestrator: Запрос + контекст сессии

    alt Нужны данные LMS
        Orchestrator->>LMSAdapter: Запрос курса / дедлайнов / прогресса
        LMSAdapter->>LMS: LMS API (read-only)
        LMS->>LMSAdapter: Raw LMS JSON
        LMSAdapter->>Orchestrator: Canonical Domain Model
    end

    alt Нужен RAG-контекст
        Orchestrator->>RAG: Semantic search + фильтры
        RAG->>Chroma: query + metadata filters
        Chroma->>RAG: топ-K фрагментов
        RAG->>Orchestrator: Контекст + источники KB
    end

    Orchestrator->>Prompt: Сборка промпта
    Prompt->>LLMAdapter: Сформированный запрос
    LLMAdapter->>LLM: LLM call
    LLM->>LLMAdapter: Сырой ответ
    LLMAdapter->>Orchestrator: Сырой ответ

    Orchestrator->>Logger: Запрос, ответ, источники, метрики
    Logger->>DB: Лог

    Orchestrator->>API: {answer, sources}
    API->>WebUI: JSON
    WebUI->>Student: Отображает ответ
```

---

## 🔄 9. Data Flow — добавление материала в Knowledge Base

```mermaid
sequenceDiagram
    participant Admin as Методист
    participant AdminConsole as Admin Console
    participant Backend as Backend
    participant DocStore as Хранилище документов
    participant DB as PostgreSQL
    participant RAG as RAG Pipeline
    participant Chroma as Chroma

    Admin->>AdminConsole: Загружает документ + метаданные
    AdminConsole->>Backend: POST /api/v1/admin/kb/documents
    Backend->>DB: Сохранение метаданных и статуса
    Backend->>DocStore: Сохранение исходного файла

    AdminConsole->>Backend: POST /process
    Backend->>RAG: Задача обработки
    RAG->>DocStore: Извлечение текста
    RAG->>RAG: Chunking + embeddings
    RAG->>Chroma: Запись в индекс
    RAG->>DB: Обновление статуса
    Backend->>AdminConsole: Обработано / ошибка
    AdminConsole->>Admin: Результат
```

---

## 🚀 10. Deployment Diagram

```mermaid
flowchart TB
    subgraph "VPS"
        direction TB
        Traefik[Traefik — reverse proxy + HTTPS]

        subgraph "AI Curator"
            WebUI3[Web UI container]
            Admin3[Admin Console container]
            Backend3[Backend container]
            Chroma3[Chroma container]
            Postgres3[PostgreSQL container]
            DocStore3[Document Store volume]
        end

        subgraph "Moodle"
            MoodleApp[Moodle container]
            MoodleDB[(Moodle DB)]
        end

        Traefik -->|ai-curator.example.com| WebUI3
        Traefik -->|ai-curator-admin.example.com| Admin3
        Traefik -->|ai-curator-api.example.com| Backend3
        Traefik -->|lms.example.com| MoodleApp

        WebUI3 --> Backend3
        Admin3 --> Backend3
        Backend3 --> Postgres3
        Backend3 --> Chroma3
        Backend3 --> DocStore3
        MoodleApp --> MoodleDB
    end

    User2[Пользователь] --> Traefik
    Backend3 -->|OpenAI API| LLM3[LLM Provider]
```

---

## 📝 11. Prompt Architecture

Prompt строится в Prompt Builder на основе активной версии `ai_configs` и конфигурации оркестратора `orchestrator_configs`.

| Часть | Назначение |
|-------|------------|
| System Prompt | Роль AI Curator, запреты, стиль |
| User Context | Курс, модуль, тема, уровень подготовки |
| LMS Data | Дедлайны, задания, прогресс из LMS (если нужно) |
| RAG Context | Найденные фрагменты Knowledge Base |
| Few-shot | Корректные и некорректные примеры ответов |
| User Question | Вопрос студента |
| Output Rules | Требования к структуре, ссылкам, отказу |

Основные параметры — версионируемые и управляются через Admin Console:

- `model`, `temperature`, `max_tokens`;
- `top_k_retrieval`, `rag_distance_threshold`;
- `beginner_instructions`, `advanced_instructions`;
- `few_shot_examples`, `output_rules`, `refusal_answer_text`;
- `max_history_messages`.

Latency-aware ограничения: LMS contents ≤ 12, deadlines ≤ 5, RAG top_k = 3 для `study`/`mixed`, intent-based `max_tokens`.

Подробная структура промптов, few-shot примеры и правила — в [`docs/PROMPT_ARCHITECTURE.md`](PROMPT_ARCHITECTURE.md).

---

## 📜 13. Logging, Analytics и Audit

### 📋 13.1. Что логируется

| Событие | Данные | Хранение | Retention |
|---------|--------|----------|-----------|
| Запрос студента | Текст, session_id, курс, уровень, lms_calls, rag_filters | PostgreSQL `chat_requests` | 30 дней в hot storage |
| Классификация | Тип запроса | PostgreSQL `chat_requests.intent` | 30 дней |
| LMS call | Endpoint, статус, latency | PostgreSQL `chat_requests.lms_calls` | 30 дней |
| RAG query | Запрос, фильтры, количество чанков | PostgreSQL `analytics_events` | 30 дней |
| LLM call metadata | Модель, токены, задержка, статус, trace_id | PostgreSQL `llm_calls` | 30 дней |
| LLM call trace | Полный prompt и response | PostgreSQL `llm_call_traces` | 7 дней |
| Ответ AI | Текст, источники, модель | PostgreSQL `chat_logs` | 30 дней |
| Latency trace | Разбивка по компонентам (intent, LMS, RAG, LLM, validation) | PostgreSQL `analytics_events.payload.timings_ms` | 30 дней |
| Оценка полезности | Оценка, комментарий | PostgreSQL `chat_logs.feedback_score` | 30 дней |
| Административное действие | Действие, пользователь, изменения | PostgreSQL `audit_logs` | 30 дней |
| Ошибка | Тип, трассировка, контекст | PostgreSQL `chat_logs.error` | 30 дней |

### 🗄️ 13.2. Retention и архивирование

Hot storage PostgreSQL хранит логи 30 дней. Полные prompt/response (`llm_call_traces`) хранятся 7 дней.

Фоновый cleanup job (`main.py::_retention_cleanup_loop`) раз в сутки:
1. Экспортирует устаревшие записи в gzip-архивы (`jsonl.gz`) в `archive_dir`.
2. Загружает записи в локальное хранилище `/app/storage/archives/` (по умолчанию).
3. Удаляет устаревшие записи из PostgreSQL.

Путь и сроки retention настраиваются переменными окружения:
- `ARCHIVE_DIR`
- `HOT_RETENTION_DAYS` (по умолчанию 30)
- `TRACE_RETENTION_DAYS` (по умолчанию 7)

### 📈 13.3. Аналитика

Admin Console отображает:

- количество запросов;
- темы вопросов;
- частые вопросы;
- вопросы без ответа;
- использованные источники;
- оценку полезности;
- задержку обработки (общая и по компонентам из `analytics_events.payload.timings_ms`);
- ошибки;
- динамику обращений по курсам и модулям.

---

## 🔐 14. Модель авторизации

### 🔌 14.1. Доступ к LMS

- LMS Adapter использует LMS API.
- Аутентификация через токен или OAuth2-сервис из переменных окружения.
- Права аккаунта ограничены read-only операциями.

### 🔐 14.2. Доступ к Admin Console

- Bearer token или аутентификация по логину/паролю.
- Ролевая модель: администратор AI Curator, методист AI Curator.
- Токен хранится в переменных окружения.

### 🌐 14.3. Web UI студента

- Гостевой доступ или аутентификация через Moodle OAuth.
- Студент видит только собственные данные и курсы.

---

## ⚡ 15. Latency Architecture

### 🎯 15.1. NFR и целевые показатели

- **NFR-1 (chat):** повторный ответ на вопрос студента — не более **5 секунд** (p50).
- **SLO:** p95 ≤ 8 сек для холодного старта (cache miss, embedding cache miss, LLM cold call); p50 ≤ 5 сек для повторных запросов (response cache hit).

### ⚡ 15.2. Компоненты оптимизации latency

| Оптимизация | Где | Эффект |
|-------------|-----|--------|
| **Embedding cache** | `src/services/rag_pipeline.py` — `_EmbeddingCache` (LRU, TTL 5 мин, размер 1000) | Повторные запросы не вызывают OpenAI Embeddings API. Холодный старт — один embedding-вызов; последующие — чтение из кэша. |
| **Parallel LMS calls** | `src/services/orchestrator.py` — `asyncio.gather(deadlines, progress, contents)` | Три LMS-вызова выполняются одновременно, а не последовательно. |
| **Parallel RAG + LMS** | `src/services/orchestrator.py` — `asyncio.gather(_fetch_lms_data, _fetch_rag_context)` для `mixed` intent | LMS-данные и RAG-контекст собираются параллельно. |
| **Reduced RAG top_k** | `src/services/orchestrator.py` — `rag_k = 3 if intent in ("study", "mixed")` | Меньше чанков в prompt → меньше токенов → быстрее LLM. |
| **RAG distance threshold** | `src/services/retrieval_tuning.py` → `retrieval_tuning.rag_distance_threshold` | `0.6` отсекает семантически далёкие чанки. При `1.35` RAG возвращал нерелевантные материалы (например, уроки Claude Code по запросу «Fine-Tuning»), что приводило к ложным источникам и неуверенным отказам. |
| **RAG deduplication** | `src/services/orchestrator.py` — content hash фильтр | Исключает дублирующиеся чанки из prompt. |
| **Reduced LMS context** | `src/services/prompt_builder.py` — `contents[:12]`, `deadlines[:5]` | Меньше текста в prompt → меньше prompt tokens. |
| **Intent-based max_tokens** | `src/services/orchestrator.py` + `src/services/llm_adapter.py` | `organizational` 250, `study` beginner 250, `mixed` 350, остальное 300. Жёстко ограничивает длину ответа и время генерации. Бюджеты хранятся в `orchestrator_configs.intent_max_tokens` и настраиваются без деплоя. |
| **Prompt trimming for advanced** | `src/services/ai_config.py` → `advanced_instructions` | Сокращены инструкции advanced-ответов: без обязательных таблиц, без Big-O, без длинных edge cases. Сохраняет структуру и технические примеры, но укладывается в token-бюджет. |
| **LLM client caching** | `src/services/llm_adapter.py` — `_get_client(max_tokens)` | Один и тот же `ChatOpenAI` клиент переиспользуется при одинаковом `max_tokens`. |
| **Short-circuit** | `src/services/orchestrator.py` | `refusal` и `progress` обходят LLM/RAG/LMS полностью или частично. |
| **Response cache** | `src/services/cache/response_cache.py` | JSON-persistent cache с TTL 24 ч. Повторные идентичные запросы возвращаются без LLM-вызова. |
| **Truncation monitoring** | `src/services/llm_adapter.py` + `services/orchestrator.py` | Если `finish_reason=length`, LLM-адаптер возвращает `error="response_truncated_by_max_tokens"`, оркестратор сохраняет флаг `llm_truncated` в `analytics_events`. |

### 📊 15.3. Разбивка latency в analytics

`analytics_events.payload.timings_ms` содержит:

| Метрика | Смысл |
|---------|-------|
| `intent_detect_ms` | Классификация сообщения |
| `lms_deadlines_ms` | LMS: дедлайны (parallel) |
| `lms_progress_ms` | LMS: прогресс (parallel) |
| `lms_contents_ms` | LMS: структура курса (parallel) |
| `rag_embedding_ms` | Время получения embedding (кэш или OpenAI) |
| `rag_chroma_ms` | Время Chroma query |
| `rag_postprocess_ms` | Дедупликация и фильтрация по distance |
| `rag_search_ms` | Общее время RAG |
| `llm_generate_ms` | Время генерации ответа LLM |
| `validation_ms` | Валидация ответа |

### ⏱️ 15.4. Методология измерений

Latency измеряется на серверной стороне и включает:
- классификацию интента;
- LMS-вызовы (parallel);
- RAG-retrieval (embedding + Chroma + postprocess);
- генерацию ответа LLM;
- валидацию и логирование.

Разбивка по компонентам доступна в `analytics_events.payload.timings_ms`. Повторяющиеся идентичные запросы обходят LLM через ResponseCache.

### ✅ 15.5. Целевые показатели

| Режим | Целевой NFR |
|-------|-------------|
| Повторные запросы (response cache hit) | p50 ≤ 5 сек |
| Холодный старт (cache miss + embedding cache miss + LLM cold call) | p95 ≤ 8 сек |
| Short-circuit (refusal / progress) | ≤ 500 мс |

Актуальные фактические замеры и методика нагрузочных тестов — в [`docs/TESTING_CONTRACT.md`](TESTING_CONTRACT.md).

---

## ✅ 16. Основные архитектурные решения

| Решение | Реализация |
|---------|------------|
| Backend — единый оркестратор | FastAPI-приложение координирует все компоненты: LMS Adapter, RAG, Prompt Builder, LLM Adapter, Answer Validator, Logging, Analytics, Audit |
| LangChain — библиотека внутри Backend | Используется только для Document Loaders, Chunking, Embeddings, Retrieval, Prompt Assembly и вызовов LLM |
| LMS — Source of Truth учебного процесса | Все учебные данные берутся из LMS API через LMS Adapter |
| Knowledge Base — самостоятельный источник знаний | Управляется через Admin Console, хранит документы, метаданные, версии; векторный индекс производный |
| LMS Adapter | Внутренний компонент Backend, изолирует AI Curator от LMS API |
| Read-only интеграция с LMS | Адаптер не выполняет операции записи |
| Web UI AI Curator | Отдельный публичный сервис на VPS с HTTPS, не встраивается в LMS |
| Admin Console AI Curator | Отдельный публичный административный интерфейс |
| HTTPS для всех сервисов | Traefik + Let's Encrypt |
| Пользовательские интерфейсы не обращаются напрямую к источникам | Все внешние обращения маршрутизируются через Backend |
| NFR latency ≤ 5 сек | Комбинация embedding cache, parallel LMS+RAG, reduced top_k, intent-based max_tokens, prompt trimming; размеры LMS-контекста и token-бюджеты по intent читаются из `orchestrator_configs` |
| Course-aware RAG | `course_id` в KB — advisory retrieval-фильтр; для study-вопросов применяется мягкий приоритет (boost), не hard filter |

---

## 💡 17. Архитектурные решения, вынесенные из Open Questions

| Вопрос | Принятое решение | Где зафиксировано |
|--------|------------------|-------------------|
| Стек Web UI / Admin Console | React 18 + Vite 5 + Tailwind CSS 3 | `docs/ADMIN_CONSOLE.md`, `docs/WEB_UI.md` |
| Модель аутентификации студента | Гостевой demo-доступ с выбором роли; Moodle OAuth — будущая опция | `docs/USER_GUIDE.md`, `docs/PROJECT_STATE.md` |
| LLM-провайдер | OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`) с опциональным fallback GigaChat | `docs/PROMPT_ARCHITECTURE.md`, `.env.example` |
| Хранилище документов Knowledge Base | Файловое хранилище внутри Backend-контейнера через Docker volume (`/app/storage/documents`) | `docs/OPERATIONS.md`, `docker-compose.yml` |
| Фоновая обработка документов | Синхронная обработка внутри Backend по endpoint'у `/admin/kb/documents/{id}/process` | `docs/API_CONTRACT.md` |
| Размер фрагментов и стратегия разбиения | 512 tokens, overlap из `retrieval_tuning` | `docs/OPERATIONS.md` |

---

## 📝 18. История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-07-29 | 1.0 | Первая версия ARCHITECTURE.md |
| 2026-07-29 | 2.0 | Пересоздана архитектура: C4 Context/Container/Component, Runtime Sequence, Data Flow, Deployment, LMS + Knowledge Base, Backend как единый оркестратор. |

---

## 📚 Связанные документы

- [🏠 `README.md`](../README.md) — главная страница проекта и live demo.
- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание системы.
- [⚙️ `docs/OPERATIONS.md`](OPERATIONS.md) — эксплуатация, KB workflow, retention.
- [🔌 `docs/API_CONTRACT.md`](API_CONTRACT.md) — API endpoints и payload.
- [📝 `docs/PROMPT_ARCHITECTURE.md`](PROMPT_ARCHITECTURE.md) — структура промптов.
- [🧪 `docs/TESTING_CONTRACT.md`](TESTING_CONTRACT.md) — стратегия и NFR-тестирование.
- [📋 `docs/SPEC.md`](SPEC.md) — продуктовая спецификация.
- [📍 `docs/PROJECT_STATE.md`](PROJECT_STATE.md) — текущее состояние и roadmap.
| 2026-07-30 | 2.1 | Добавлены retention, параметризация промптов, latency-разбивка |
| 2026-07-31 | 2.2 | Добавлены LMS-KB Linking Contract и конфигурируемая маршрутизация запросов через `orchestrator_configs` |
| 2026-08-01 | 2.3 | Добавлены Execution Tracing (`chat_sessions`, `execution_sessions`, `execution_steps`), обновлена схема аудита с `ip_address`/`user_name` |
| 2026-08-02 | 2.4 | Добавлен ResponseCache с инвалидацией, тестовая БД и Testing Cost Contract, убран read-only аудит |
| 2026-08-05 | 2.5 | Актуализация Deployment Diagram, устранение дублирования номеров разделов, замена Open Questions на таблицу решений, сокращение Prompt Architecture, добавлены Sprint F (safe demo mode), Business Reports, log export/retention, RBAC demo admin |
