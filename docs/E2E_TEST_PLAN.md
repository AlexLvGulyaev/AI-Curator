# 🧪 AI Curator — Product E2E Test Plan

**Проект:** ai-curator  
**Версия:** 1.1  
**Дата:** 2026-08-05  
**Статус:** Active — Phase 1 выполнен; Phase 2 встроен в чек-лист и готов к прогону

---

## 🎯 1. Назначение

Этот документ определяет стратегию сквозного (end-to-end) тестирования AI Curator как продукта. В отличие от `TESTING_CONTRACT.md`, который описывает автоматизированные backend-тесты, и `ORCHESTRATOR_E2E_CHECKLIST.md`, который проверяет только интеллектуальное ядро, E2E Test Plan охватывает полный путь пользователя:

> **Реальный человек → Web UI / Admin Console → Backend → LMS / Knowledge Base / LLM → ответ в UI → запись в логах и аудите.**

---

## 📦 2. Границы E2E

### ✅ 2.1 Внутри области покрытия (Phase 1 — завершён)

- Гостевой вход в Web UI и выбор роли студента.
- Чат-диалог: вопросы организационные, учебные, смешанные, fallback.
- Источники ответа (Knowledge Base, LMS), переключатель сложности, кэш.
- Admin Console: аутентификация, Knowledge Base CRUD, публикация, обработка, индексация.
- Admin Console: AI & Retrieval Configuration, Orchestrator Configuration.
- Observability: Operational Logs, Dialog Sessions, Audit Log.
- Deployment Validation по `DEPLOYMENT_GUIDE.md`.
- Корректность client IP в audit/chat логах (real IP vs Docker internal IP).

### 📦 2.2 Phase 2 — реализован и встроен в чек-лист

Phase 2-фичи разработаны и отражены в `PRODUCT_E2E_CHECKLIST.md`:

- Analytics Dashboard (`/api/v1/admin/analytics/*`) — Sprint E1.
- Business / Quality Reports (`/api/v1/admin/reports/*`) — Sprint E2.
- Read-only demo admin + RBAC в Admin Console — Sprint A2/A3.
- Safe Web UI demo mode с `X-Demo-Token`, квотами и rate limit — Sprint F.
- CSV-экспорт operational logs, audit, dialog sessions — логирование и retention.

### 🚧 2.3 Вне области / запланировано позже

- Автоматизация UI через Playwright/Cypress — остаётся в Phase 2 (PH2-05).
- Интеграционные и unit-тесты backend — см. `TESTING_CONTRACT.md`.

---

## 👥 3. Роли и ответственность

| Роль | Обязанности |
|---|---|
| **QA / Внедренец** | Выполняет ручные E2E-сценарии из `PRODUCT_E2E_CHECKLIST.md`, фиксирует статусы и дефекты. |
| **Разработчик** | Исправляет дефекты, обновляет чек-лист после изменений, поддерживает pytest-комплект. |
| **DevOps** | Обеспечивает работоспособность prod-окружения, Traefik-маршрутов, SSL и лимитов. |
| **Product Owner / Куратор** | Утверждает критерии приёмки и приоритет E2E-сценариев. |

---

## 🔄 4. Частота прогонов

| Триггер | Что прогоняем | Кто |
|---|---|---|
| Каждый backend deploy | Smoke: health endpoints + один чат-запрос + одна Admin Console операция | DevOps |
| После изменений Orchestrator / KB / AI config | Релевантные сценарии из `PRODUCT_E2E_CHECKLIST.md` | QA |
| Перед публикацией кейса / релизом | Все ручные сценарии Phase 1 + Deployment Validation | QA + DevOps |
| После добавления Analytics / Reports / Demo modes | Phase 2 — дополнительные сценарии | QA |

---

## 🛠️ 5. Инструменты

| Этап | Инструмент | Назначение |
|---|---|---|
| Phase 1 | Ручные проверки в браузере + curl/httpx | Проверка пользовательских путей без затрат на автоматизацию. |
| Phase 1 | `docker logs`, `docker exec psql` | Проверка данных в БД, audit log, operational logs. |
| Phase 2 | Playwright | Автоматизация Web UI и Admin Console. |
| Phase 2 | GitHub Actions (опционально) | CI-прогон Playwright-тестов на staging. |

---

## ✅ 6. Критерии приёмки E2E

Сценарий считается **PASS**, если:

1. Все шаги в `PRODUCT_E2E_CHECKLIST.md` выполнены без ошибок.
2. UI отображает ожидаемый результат.
3. Backend вернул корректный ответ (HTTP 2xx, корректный payload).
4. В `audit_logs` появилась запись с правильным `action`, `user_id`, `ip_address`, `details`.
5. В `operational_logs` / `dialog_sessions` отражены шаги обработки запроса.
6. Кэш инвалидируется после изменений конфигурации / KB (проверяется через повторный запрос).

Сценарий считается **FAIL**, если любой из пунктов нарушен, даже при косметически корректном UI.

---

## 📍 7. Входные точки тестирования

| Интерфейс | URL |
|---|---|
| Web UI студента | `https://ai-curator.example.com` |
| Admin Console | `https://ai-curator-admin.example.com` |
| Backend API | `https://ai-curator-api.example.com` |
| Moodle LMS | `https://lms.example.com` |

---

## 📚 8. Связанные документы

- [📋 PRODUCT_E2E_CHECKLIST.md](PRODUCT_E2E_CHECKLIST.md) — конкретные ручные сценарии и шаги.
- [📋 ORCHESTRATOR_E2E_CHECKLIST.md](ORCHESTRATOR_E2E_CHECKLIST.md) — детальные проверки оркестратора.
- [🧪 TESTING_CONTRACT.md](TESTING_CONTRACT.md) — автоматизированные backend-тесты.
- [🚀 DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) — инструкции для Deployment Validation.
- [🎬 E2E_SCENARIOS.md](E2E_SCENARIOS.md) — бизнес-сценарии.
- [📍 PROJECT_STATE.md](PROJECT_STATE.md) — актуальный статус E2E и открытые задачи.

---

## ⚠️ 9. Риски и митигация

| Риск | Влияние | Митигация |
|---|---|---|
| LLM API недоступен или дорог | Прогон chat-сценариев блокируется | Использовать кэшированные ответы и deterministic fallback-сценарии. |
| Moodle API недоступен | Блокирует organizational/progress сценарии | Проверять health LMS отдельно, иметь fallback. |
| Chroma коллекция пуста | Блокирует RAG-сценарии | Загружать демо-материалы перед прогоном. |
| Ручные прогоны занимают много времени | Медленный feedback loop | Phase 2 — автоматизация через Playwright. |

---

## 📝 10. Изменение плана

Любое добавление в продукт, меняющее пользовательский путь (новая консоль, новый интент, demo mode), требует обновления этого документа и [`PRODUCT_E2E_CHECKLIST.md`](PRODUCT_E2E_CHECKLIST.md).

---

## 📜 История изменений

| Дата | Версия | Изменение |
|---|---|---|
| 2026-08-04 | 1.0 | Начальная версия Phase 1 |
| 2026-08-05 | 1.1 | Актуализация: Phase 1 завершён, Phase 2-фичи встроены в чек-лист, применён emoji-контракт, связанные документы приведены к единому стилю |
