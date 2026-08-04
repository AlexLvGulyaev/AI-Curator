# PROJECT_STATE.md — AI Curator

**Проект:** ai-curator
**Дата создания:** 2026-07-29
**Последнее обновление:** 2026-08-04
**Статус:** Implementation In Progress — Day 7 extended into stabilization sprints A–E; UI unification and E2E in progress; Analytics + Business Reports + Demo modes planned

---

## Project Summary

AI Curator — самостоятельная подсистема образовательной платформы, которая помогает студентам ориентироваться в учебном процессе, находить ответы в учебных материалах, разбирать сложные темы и получать персональные рекомендации.

Система работает с двумя независимыми источниками данных:

- **LMS** — Source of Truth учебного процесса (курсы, модули, пользователи, задания, дедлайны, расписание, прогресс, оценки).
- **Knowledge Base AI Curator** — самостоятельный источник учебных материалов (лекции, методички, FAQ), управляемый через Admin Console AI Curator.

AI Curator не заменяет преподавателя, не выставляет оценки и не изменяет учебный процесс. Система разворачивается на VPS как полноценный публичный сервис.

## Current Status

**Implementation In Progress.**

Документы PROJECT_STATE.md, SPEC.md, ARCHITECTURE.md и IMPLEMENTATION_PLAN.md согласованы куратором. Дни 1–6 IMPLEMENTATION_PLAN выполнены, Sprint 5 (Admin Console panels) и Sprint 6.1 (Configurable Orchestrator Routing) завершены. Проект находится в серии спринтов стабилизации и подготовки к аналитике (раздел 10 IMPLEMENTATION_PLAN), которые превратили "День 7" в многосессионный завершающий этап.

**Что уже реализовано и развёрнуто:**

- Moodle LMS развёрнута на VPS и доступна по HTTPS: `https://lms.alex-n8n.site`.
- Домены и Traefik-маршруты настроены для всех публичных сервисов AI Curator.
- В Moodle создан демо-курс «Claude Code: от знакомства до автоматизации» (AI Skills Lab) с тремя модулями, уроками, обратной связью, заданиями и дедлайнами.
- Созданы тестовые пользователи и роли (student, teacher, manager); включены Moodle Web Services; создан read-only API-токен для интеграции.
- Backend AI Curator развёрнут на `https://curator-api.alex-n8n.site`.
- LMS Adapter: курсы, дедлайны, прогресс из Moodle.
- Knowledge Base: модели PostgreSQL, файловое хранилище, Admin API CRUD, версионирование, обработка, публикация, индексация, RAG через LangChain + OpenAI + Chroma.
- Web UI студента на React + Vite + Tailwind CSS, развёрнут на `https://curator.alex-n8n.site`, с гостевым демо-входом и ролями (`active_student`, `late_student`, `new_student`).
- Admin Console на React + Vite + Tailwind CSS (тёмная тема AI Portfolio), развёрнут на `https://curator-admin.alex-n8n.site`.
- Admin Console panels: Dashboard, AI & Retrieval Configuration, Orchestrator Configuration, Knowledge Base Documents, Operational Logs, Dialog Sessions, Audit Log.
- LLM Chat core: Prompt Builder, LLM Adapter, Answer Validator, Orchestrator с конфигурируемой интент-классификацией и source routing.
- Execution tracing: `chat_sessions`, `execution_sessions`, `execution_steps`; timeline в консоли Dialog Sessions.
- ResponseCache: кэширование запросов, инвалидация при мутациях KB/AI/retrieval/orchestrator, `cache_hit` в API и UI.
- Logging & Analytics: `chat_requests`, `chat_logs`, `llm_calls`, `analytics_events`, `audit_logs`.
- Audit backend: фильтры по дате, действию, типу ресурса, пользователю; детальная карточка с `user_id`, `user_name`, `ip_address`, `details`.
- E2E testing strategy: `docs/E2E_TEST_PLAN.md` + `docs/PRODUCT_E2E_CHECKLIST.md` для ручных сквозных прогонов.
- Auth: Admin Console защищён Bearer-токеном `ADMIN_CONSOLE_TOKEN`.
- Testing infrastructure: тестовая БД `ai_curator_test`, Alembic-миграции в тестах, маркеры pytest, `docs/TESTING_CONTRACT.md`.
- `pytest` стабильно проходит (53+ тестов).

**Оставшиеся ключевые работы:**

1. **Спринт E1 — Analytics Dashboard:** полноценный дашборд с фильтрами по периоду/курсу, latency histograms, топ источников, ошибками, распределением интентов.
2. **Спринт E2 — Business Reports / Quality Reports:** управленческая сводка — вопросы без ответа, гэпы Knowledge Base, популярные темы, кандидаты на расширение KB.
3. **Спринт A2/A3 — Read-only demo admin + RBAC:** безопасный демо-доступ в Admin Console только на просмотр, запрет изменений для demo-роли.
4. **Web UI safe demo mode:** ограниченный по запросам/расходу API режим для потенциальных клиентов на публичном Web UI с защитой API-лимитов.
5. **Продуктовое E2E-тестирование и документирование (Phase 1):** созданы `docs/E2E_TEST_PLAN.md` и `docs/PRODUCT_E2E_CHECKLIST.md`, охватывающие Web UI студента, Admin Console, Observability и Deployment Validation. Требуется выполнить первый полный ручной прогон и зафиксировать дефекты.
6. **Phase 2 E2E:** дополнить чек-лист сценариями Analytics, Business Reports, read-only demo admin / RBAC и safe Web UI demo mode по мере реализации фич.
7. **Актуализация DEPLOYMENT_GUIDE.md и README.md:** подготовка материалов для портфолио.

## Market Validation

**Источник запроса:** функциональные требования заказчика.

Рынок образовательных AI-ассистентов растёт. Потребность в персонализированной поддержке студентов подтверждается распространением LMS, онлайн-курсов и повторяющимися вопросами преподавателям. Конкретные заказы и сделки на данном этапе не зафиксированы.

## Commercial Assessment

**Коммерческий потенциал:** Высокий для образовательных платформ, корпоративных учебных центров и преподавателей с курсами на LMS.

**Востребованность:** Средне-высокая. Решение закрывает типовой pain-point: снижение нагрузки на преподавателей и повышение вовлечённости студентов.

**Основные риски:**
- Зависимость от корректности и доступности данных LMS.
- Стоимость LLM API при масштабировании.
- Необходимость тщательного контроля качества ответов AI.
- Требования к безопасности и конфиденциальности студенческих данных.
- Необходимость управления Knowledge Base отдельно от LMS.

## Key Technology Areas

| Область | Компетенция / решение | Статус |
|---------|----------------------|--------|
| LMS | Moodle | ✅ Развёрнуто и настроено |
| Backend | FastAPI | ✅ Дни 1–3 + спринты завершены |
| LLM | OpenAI API | ✅ Ключ добавлен в `.env` |
| Embeddings | OpenAI API | ✅ Ключ добавлен в `.env` |
| AI / RAG библиотека | LangChain (внутри Backend) | ✅ Sprint 4.2 + оптимизации выполнены |
| Операционная база | PostgreSQL | ✅ Развёрнута, миграции применены |
| Векторный индекс | Chroma | ✅ Развёрнута, health check проходит |
| Хранилище документов KB | Файловое хранилище внутри Backend-контейнера (volume `/app/storage/documents`) | ✅ Реализовано |
| Web UI студента | React + Vite + Tailwind CSS | ✅ Развёрнут на `https://curator.alex-n8n.site` |
| Admin Console | React + Vite + Tailwind CSS | ✅ Развёрнут на `https://curator-admin.alex-n8n.site`; UI унифицирован |
| Контейнеризация | Docker + Docker Compose | ✅ Все сервисы развёрнуты |
| Reverse proxy / HTTPS | Traefik + Let's Encrypt | ✅ Работает для всех публичных сервисов |
| Кэширование запросов | ResponseCache (PostgreSQL/локальное) | ✅ Интегрировано в Orchestrator и UI |
| Execution tracing | `chat_sessions` + `execution_sessions` + `execution_steps` | ✅ Развёрнуто |
| Тестирование | pytest + тестовая БД + маркеры | ✅ Инфраструктура готова |

## Decision

**Принято:** разработать AI Curator как самостоятельный публичный сервис на VPS, интегрированный с Moodle LMS через LMS Adapter.

**Утверждённые решения:**
- LMS (Moodle) — единственный Source of Truth учебного процесса.
- Knowledge Base AI Curator — самостоятельный источник учебных материалов, не являющийся частью LMS.
- AI Curator получает данные из LMS в режиме read-only.
- AI Curator не изменяет оценки, задания, расписание, дедлайны и учебный прогресс.
- Backend AI Curator — единый оркестратор всех пользовательских и административных сценариев.
- LangChain используется только как внутренняя библиотека Backend.
- LMS Adapter — внутренний компонент Backend.
- Web UI AI Curator — отдельный публичный интерфейс на VPS, доступный по собственному HTTPS-эндпоинту.
- Admin Console AI Curator — отдельный публичный административный интерфейс.
- Пользовательские интерфейсы не обращаются напрямую к LMS, Knowledge Base, векторному индексу или LLM.
- Все публичные сервисы доступны по HTTPS.

## Next Steps

1. ✅ Согласовать PROJECT_STATE, SPEC, ARCHITECTURE и IMPLEMENTATION_PLAN.
2. ✅ Утвердить технологический стек frontend, LLM-провайдера и хостинг.
3. ✅ Зарезервировать VPS и домены.
4. ✅ Получить API-ключ LLM-провайдера.
5. ✅ Подготовить учебный курс в LMS.
6. ✅ Дни 1–6 IMPLEMENTATION_PLAN выполнены.
7. ✅ Sprint 5 (Admin Console panels) и Sprint 6.1 (Orchestrator Config) завершены.
8. ✅ Sprint C (ResponseCache) завершён.
9. ✅ Sprint A1 (read-only audit cleanup) выполнен.
10. ✅ Sprint B (test DB, testing contract, prod cleanup) выполнен.
11. ✅ Завершить ручной E2E Admin Console (Sprint D).
12. 🔄 Выполнить первый прогон `docs/PRODUCT_E2E_CHECKLIST.md` (Phase 1).
13. ⏳ Реализовать Analytics Dashboard (Sprint E1).
13. ⏳ Реализовать Business Reports / Quality Reports (Sprint E2).
14. ⏳ Реализовать read-only demo login и RBAC в Admin Console (Sprint A2/A3).
15. ⏳ Реализовать безопасный API-лимитированный demo режим на Web UI.
16. ⏳ Актуализировать DEPLOYMENT_GUIDE.md и README.md для портфолио.

## Open Questions

| Вопрос | Категория | Примечание |
|--------|-----------|------------|
| Какой LLM-провейдер использовать? | Технология | ✅ Решено: OpenAI API, `gpt-4o-mini`, `text-embedding-3-small` |
| Какой стек для Web UI и Admin Console? | Технология | ✅ Решено: React + Vite + Tailwind CSS; Admin Console — тёмная тема AI Portfolio |
| Какие конкретные домены и VPS? | Инфраструктура | ✅ Решено: домены направлены на VPS, Traefik-маршруты и SSL-сертификаты настроены |
| Какой курс будет использоваться для демонстрации? | Контент | ✅ Решено: «Claude Code: от знакомства до автоматизации» (AI Skills Lab), 3 модуля, id: 3 |
| Как организовать хранилище документов Knowledge Base? | Инфраструктура | ✅ Решено: файловое хранилище внутри Backend-контейнера через Docker volume |
| Нужна ли аутентификация студентов в Web UI? | Безопасность | ✅ Решено: гостевой демо-доступ с выбором ролей; Moodle OAuth / SSO — будущая опция |
| Какие метрики аналитики критичны? | Продукт | ✅ Решено: total_requests, intent_distribution, unanswered_count, average_latency_ms, feedback_score_distribution |
| Как защитить API-лимиты в demo-режиме Web UI? | Безопасность / Cost | ⏳ Открыто: требуется rate limiting, квоты на сессию, кэширование, возможно капча |
| Нужен ли read-only demo-доступ в Admin Console? | Безопасность | ⏳ Открыто: запланировано в Sprint A2/A3 |

## Dependencies

| Зависимость | Описание | Влияние |
|-------------|----------|---------|
| Moodle | Необходим экземпляр с курсом и тестовыми пользователями | Блокирует интеграцию и организационные сценарии |
| VPS и домены | Требуются для публичного развёртывания Web UI, Admin Console и Backend | Блокирует деплой |
| LLM API | Необходим API-ключ и доступ к сервису | Блокирует генерацию ответов |
| Knowledge Base content | Необходимы учебные материалы для RAG | Блокирует содержательные ответы |
| Куратор / владелец | Согласование концепции и плана | Блокирует старт реализации |

## Risks

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|--------|------------|
| Недоступность Moodle API | Низкая | Высокое | Резервный тестовый курс, проверка прав доступа, graceful degradation |
| Высокая стоимость LLM API | Средняя | Среднее | Кэширование, rate limiting, выбор модели, demo-квоты |
| Некорректные ответы AI | Средняя | Высокое | RAG с источниками, few-shot примерами, answer validation, логирование |
| Сложности с HTTPS / доменами | Низкая | Среднее | Использовать проверенные инструменты: Traefik + Let's Encrypt |
| Изменение требований заказчика | Средняя | Среднее | Регулярное согласование, фиксация решений в PROJECT_STATE |
| Безопасность студенческих данных | Низкая | Высокое | Read-only интеграция, шифрование, минимизация хранимых данных, разграничение доступа |
| Наполнение Knowledge Base | Средняя | Высокое | Подготовить методистский процесс и контент заранее |
| Перерасход API-лимитов в demo-режиме | Средняя | Среднее | Rate limiting, квоты на сессию, кэширование, ограничение длины диалога |

## Readiness Criteria for Implementation

Переход к реализации возможен когда:
- [x] Подготовлен PROJECT_STATE.md.
- [x] Подготовлен SPEC.md.
- [x] Подготовлен ARCHITECTURE.md.
- [x] Подготовлен IMPLEMENTATION_PLAN.md.
- [x] Куратор утвердил концепцию и план.
- [x] Выбран и доступен VPS.
- [x] Зарезервированы домены.
- [x] Получен API-ключ LLM-провайдера.
- [x] Подготовлен или выбран учебный курс в LMS.
- [x] Подготовлены учебные материалы для Knowledge Base (19 документов, 40 чанков).

## Status History

| Дата | Статус | Примечание |
|------|--------|------------|
| 2026-07-29 | Discovery and Architecture | Созданы PROJECT_STATE, SPEC, ARCHITECTURE, IMPLEMENTATION_PLAN. Ожидание согласования. |
| 2026-07-29 | Approved for Implementation | Документы согласованы куратором. Проект готов к реализации. |
| 2026-07-29 | Implementation In Progress | Выполнены День 1 и День 2: Moodle, курс, роли, API-токен. |
| 2026-07-29 | Implementation In Progress | Выполнен День 3: Backend scaffold, LMS Adapter, PostgreSQL, Chroma, health endpoints, базовые API, тесты. |
| 2026-07-29 | Implementation In Progress | Выполнен Sprint 4.1: Knowledge Base scaffold, Admin API, миграции, тесты. |
| 2026-07-29 | Implementation In Progress | Выполнен Sprint 4.2: RAG pipeline, обработка документов, Chroma search. |
| 2026-07-29 | Implementation In Progress | Выполнен День 5: Web UI студента, гостевой demo-вход, чат с источниками. |
| 2026-07-30 | Implementation In Progress | Выполнен День 6: LLM Chat, Admin Console scaffold, logging, analytics, audit, deploy. |
| 2026-08-04 | Implementation In Progress — Stabilization Sprints | Завершены Sprint 5 (Admin Console panels), Sprint 6.1 (Orchestrator Config), Sprint C (ResponseCache), Sprint A1 (read-only audit cleanup), Sprint B (testing infrastructure). UI консолей унифицирован. Остались Sprint D (E2E), Sprint E (Analytics + Reports), Sprint A2/A3 (demo admin + RBAC), Web UI safe demo mode, финальная документация. |
