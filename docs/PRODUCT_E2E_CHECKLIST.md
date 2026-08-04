# AI Curator — Product E2E Checklist

**Версия:** 1.0  
**Дата:** 2026-08-04  
**Статус:** Phase 1 — ручные прогоны  

---

## Как пользоваться этим чек-листом

Каждая строка — это сквозной сценарий. Выполняйте шаги в UI, сверяйте с *Ожидаемым результатом*, отмечайте статус и фиксируйте дефекты. Сценарий считается `PASS` только если совпадают UI, API-ответ, данные в БД и audit/observability.

**Статусы:** `PASS` / `FAIL` / `BLOCKED` / `NOT RUN`  
**Исполнитель:** ______________  
**Дата прогона:** ______________

---

## Сокращения

| Сокращение | Расшифровка |
|---|---|
| UI | Пользовательский интерфейс |
| KB | Knowledge Base AI Curator |
| AC | Admin Console |
| LMS | Moodle Learning Management System |
| RAG | Retrieval-Augmented Generation (поиск по KB) |

---

## Предусловия для всего чек-листа

- [ ] Все контейнеры AI Curator запущены и healthy (`docker compose ps`).
- [ ] Backend health возвращает `{"status":"ok"}` (`curl https://curator-api.alex-n8n.site/health`).
- [ ] Web UI доступен по `https://curator.alex-n8n.site`.
- [ ] Admin Console доступен по `https://curator-admin.alex-n8n.site`.
- [ ] В Moodle создан демо-курс с дедлайнами и прогрессом (id: 3).
- [ ] В KB загружены и опубликованы материалы по курсу.
- [ ] Известен `ADMIN_CONSOLE_TOKEN` для AC.

---

## Раздел 1. Студент — Web UI

### 1.1 Гостевой вход и выбор роли

| Поле | Значение |
|---|---|
| **ID** | STU-01 |
| **User Journey** | Новый пользователь открывает Web UI и выбирает роль. |
| **Preconditions** | Очищены cookies/localStorage, чистая сессия. |
| **Steps** | 1. Открыть `https://curator.alex-n8n.site`. <br>2. Убедиться, что открылась страница выбора роли. <br>3. Выбрать `active_student`. <br>4. Убедиться, что открылся чат с курсом «Claude Code: от знакомства до автоматизации». |
| **Expected Result** | Отображается чат, в шапке — роль «Активный студент», курс выбран, backend online. |
| **Backend / Data Checks** | В `audit_logs` нет новой записи (гостевой вход не аудируется). В `chat_sessions` может быть создана сессия только после первого сообщения. |
| **Status** | |
| **Notes** | |

### 1.2 Смена роли

| Поле | Значение |
|---|---|
| **ID** | STU-02 |
| **User Journey** | Студент меняет роль внутри чата. |
| **Preconditions** | Выполнен STU-01. |
| **Steps** | 1. Нажать «Сменить роль». <br>2. Выбрать `late_student`. <br>3. Убедиться, что открылся чат с той же страницы выбора роли. |
| **Expected Result** | Роль изменилась, курс тот же, история сообщений сброшена. |
| **Backend / Data Checks** | В `chat_sessions` новая сессия с `role=late_student`. |
| **Status** | |
| **Notes** | |

### 1.3 Организационный вопрос: дедлайн

| Поле | Значение |
|---|---|
| **ID** | STU-03 |
| **User Journey** | Студент спрашивает про срок сдачи. |
| **Preconditions** | Orchestrator config: `deadline` → LMS=true, RAG=false, Strict=true. |
| **Steps** | 1. В чате выбрать курс. <br>2. Отправить: «Когда дедлайн по следующему заданию?» |
| **Expected Result** | Ответ содержит конкретный ближайший дедлайн с датой и названием задания. Источники KB не упоминаются. `intent=deadline`. |
| **Backend / Data Checks** | В `chat_requests`: `intent=deadline`, `rag_filters` пуст или не используется. В `audit_logs` — `chat_request`, `ip_address` = реальный IP. В `execution_sessions` — шаги LMS. |
| **Status** | |
| **Notes** | |

### 1.4 Учебный вопрос: Knowledge Base

| Поле | Значение |
|---|---|
| **ID** | STU-04 |
| **User Journey** | Студент спрашивает учебную тему. |
| **Preconditions** | Orchestrator config: `study` → LMS=false, RAG=true, Strict=false; в KB есть материал по теме. |
| **Steps** | 1. Отправить: «Раскрой тему промпт-инжиниринга.» |
| **Expected Result** | Ответ содержит материал из KB, ссылки/источники на документы KB. `intent=study`. |
| **Backend / Data Checks** | В `chat_requests`: `intent=study`, `rag_filters` непустой. В `execution_sessions` — шаг `context_build` с `rag_context`. |
| **Status** | |
| **Notes** | |

### 1.5 Fallback: нет данных в KB

| Поле | Значение |
|---|---|
| **ID** | STU-05 |
| **User Journey** | Вопрос вне области KB. |
| **Preconditions** | Orchestrator config: `study` → RAG=true; fallback `no_rag_context` задан явным текстом. |
| **Steps** | 1. Отправить: «Расскажи про квантовые вычисления.» |
| **Expected Result** | Ответ содержит текст fallback `no_rag_context`, без выдуманных данных. |
| **Backend / Data Checks** | В `chat_logs`/`execution_sessions` отмечен fallback. |
| **Status** | |
| **Notes** | |

### 1.6 Fallback: нет прогресса в LMS

| Поле | Значение |
|---|---|
| **ID** | STU-06 |
| **User Journey** | Новый студент спрашивает о прогрессе. |
| **Preconditions** | Роль `new_student`; в Moodle у пользователя нет прогресса; fallback `no_lms_data` задан. |
| **Steps** | 1. Выбрать `new_student`. <br>2. Отправить: «Какие модули я уже прошёл?» |
| **Expected Result** | Ответ содержит fallback `no_lms_data`. |
| **Backend / Data Checks** | В `chat_requests`: `intent=progress`. В `execution_sessions` — LMS-вызов с пустым результатом и fallback. |
| **Status** | |
| **Notes** | |

### 1.7 Переключатель сложности

| Поле | Значение |
|---|---|
| **ID** | STU-07 |
| **User Journey** | Студент переключает уровень сложности. |
| **Preconditions** | В AI config заданы разные `beginner_instructions` и `advanced_instructions`. |
| **Steps** | 1. Отправить вопрос на уровне `beginner`. <br>2. Переключить на `advanced`. <br>3. Задать тот же вопрос. |
| **Expected Result** | `beginner`-ответ простой, без жаргона. `advanced`-ответ структурированный: таблица, код, Big-O, edge cases. Разница визуально заметна. |
| **Backend / Data Checks** | В `chat_requests`: `difficulty` меняется. В `llm_calls` — разные prompt/system prompt. |
| **Status** | |
| **Notes** | |

### 1.8 Кэширование

| Поле | Значение |
|---|---|
| **ID** | STU-08 |
| **User Journey** | Повторный вопрос возвращает кэшированный ответ. |
| **Preconditions** | ResponseCache включён. |
| **Steps** | 1. Задать вопрос и дождаться ответа. <br>2. Задать тот же вопрос в той же сессии с теми же параметрами. |
| **Expected Result** | Второй ответ пришёл быстрее, в UI есть индикатор `cache_hit=true`. |
| **Backend / Data Checks** | В `chat_logs`: `cache_hit=true` для второго запроса. В `llm_calls` нет новой записи для второго запроса. |
| **Status** | |
| **Notes** | |

---

## Раздел 2. Администратор — Admin Console

### 2.1 Вход по токену

| Поле | Значение |
|---|---|
| **ID** | ADM-01 |
| **User Journey** | Администратор открывает Admin Console. |
| **Preconditions** | `ADMIN_CONSOLE_TOKEN` известен. |
| **Steps** | 1. Открыть `https://curator-admin.alex-n8n.site`. <br>2. Ввести токен. <br>3. Нажать «Войти». |
| **Expected Result** | Открывается Dashboard Admin Console, Sidebar с пунктами меню. |
| **Backend / Data Checks** | В `audit_logs` нет записи о входе (read-only view). |
| **Status** | |
| **Notes** | |

### 2.2 Загрузка документа в KB

| Поле | Значение |
|---|---|
| **ID** | ADM-02 |
| **User Journey** | Администратор добавляет лекцию в Knowledge Base. |
| **Preconditions** | Подготовлен `.md`-файл с лекцией. |
| **Steps** | 1. Перейти в раздел «База знаний». <br>2. Нажать «Загрузить версию». <br>3. Заполнить title, document_type, course_id. <br>4. Выбрать файл. <br>5. Нажать «Сохранить». |
| **Expected Result** | Документ появился в списке со статусом `pending`, версия 1. |
| **Backend / Data Checks** | В `audit_logs`: `action=create`, `resource_type=kb_document`, `details.title` заполнен, `ip_address` = реальный IP. |
| **Status** | |
| **Notes** | |

### 2.3 Обработка и публикация документа

| Поле | Значение |
|---|---|
| **ID** | ADM-03 |
| **User Journey** | Документ обрабатывается, чанки создаются, документ публикуется. |
| **Preconditions** | Выполнен ADM-02, документ в статусе `pending`. |
| **Steps** | 1. Открыть детали документа. <br>2. Нажать «Обработать». <br>3. Дождаться статуса `processed`. <br>4. Нажать «Опубликовать». |
| **Expected Result** | Статус документа `published`, в detail видны чанки, active version установлена. |
| **Backend / Data Checks** | В `audit_logs`: `action=process` и `action=publish`. В Chroma появились embeddings. |
| **Status** | |
| **Notes** | |

### 2.4 Редактирование cleaned-текста

| Поле | Значение |
|---|---|
| **ID** | ADM-04 |
| **User Journey** | Методист правит cleaned-текст версии и переиндексирует. |
| **Preconditions** | Выполнен ADM-03. |
| **Steps** | 1. Открыть версию документа. <br>2. Нажать «Редактировать текст». <br>3. Внести изменение. <br>4. Сохранить с переиндексацией. |
| **Expected Result** | Версия обновлена, новые чанки в Chroma соответствуют отредактированному тексту. |
| **Backend / Data Checks** | В `audit_logs`: `action=save_cleaned_text`, `details.reindex=true`. |
| **Status** | |
| **Notes** | |

### 2.5 Изменение AI Configuration

| Поле | Значение |
|---|---|
| **ID** | ADM-05 |
| **User Journey** | Администратор меняет system prompt / модель. |
| **Preconditions** | AC открыт, раздел «AI и Retrieval». |
| **Steps** | 1. Перейти в «AI и Retrieval». <br>2. Изменить system prompt. <br>3. Нажать «Сохранить». |
| **Expected Result** | Появилась новая версия конфигурации, кэш чата сброшен. |
| **Backend / Data Checks** | В `audit_logs`: `action=create`, `resource_type=ai_config`, `details.name` и `details.model`. Response cache invalidated. |
| **Status** | |
| **Notes** | |

### 2.6 Изменение Orchestrator Configuration

| Поле | Значение |
|---|---|
| **ID** | ADM-06 |
| **User Journey** | Администратор меняет source routing для интента. |
| **Preconditions** | AC открыт, раздел «Orchestrator». |
| **Steps** | 1. Перейти в «Orchestrator». <br>2. Для `deadline` отключить LMS, включить RAG. <br>3. Сохранить. <br>4. В Web UI задать вопрос про дедлайн. |
| **Expected Result** | Ответ на вопрос про дедлайн изменился: больше не содержит LMS-данных, срабатывает fallback. |
| **Backend / Data Checks** | В `audit_logs`: `action=update`, `resource_type=orchestrator_config`, `details.changed_fields`. Кэш сброшен. |
| **Status** | |
| **Notes** | |

### 2.7 Operational Logs

| Поле | Значение |
|---|---|
| **ID** | ADM-07 |
| **User Journey** | Администратор проверяет логи запросов. |
| **Preconditions** | Выполнены студенческие сценарии STU-03..STU-08. |
| **Steps** | 1. Перейти в «Логи». <br>2. Применить фильтр по intent. <br>3. Открыть детальную карточку запроса. |
| **Expected Result** | В таблице отображаются запросы с intent, latency, cache_hit. В деталях видны шаги pipeline, RAG-чанки, LMS-вызовы. |
| **Backend / Data Checks** | Данные в `operational_logs` / `execution_sessions` соответствуют UI. |
| **Status** | |
| **Notes** | |

### 2.8 Dialog Sessions

| Поле | Значение |
|---|---|
| **ID** | ADM-08 |
| **User Journey** | Администратор смотрит диалог студента. |
| **Preconditions** | Выполнен STU-03 или STU-04. |
| **Steps** | 1. Перейти в «Диалоги». <br>2. Найти сессию по `session_id`. <br>3. Открыть детали. |
| **Expected Result** | Видны сообщения студента и AI, intent, sources, latency, таймлайн pipeline. |
| **Backend / Data Checks** | Данные в `chat_sessions` + `execution_sessions` соответствуют UI. |
| **Status** | |
| **Notes** | |

### 2.9 Audit Log

| Поле | Значение |
|---|---|
| **ID** | ADM-09 |
| **User Journey** | Администратор проверяет аудит изменений. |
| **Preconditions** | Выполнены ADM-02..ADM-06. |
| **Steps** | 1. Перейти в «Аудит». <br>2. Отфильтровать по `action=create` и `resource_type=kb_document`. <br>3. Открыть детальную карточку. |
| **Expected Result** | Видны все mutating admin-операции: user_id, user_name, ip_address, details. Read-only views не создают новых записей. |
| **Backend / Data Checks** | `audit_logs` содержит записи с непустыми `user_name` и `ip_address`. |
| **Status** | |
| **Notes** | |

---

## Раздел 3. Cross-cutting и негативные сценарии

### 3.1 Кэш инвалидации после изменения конфигурации

| Поле | Значение |
|---|---|
| **ID** | CROSS-01 |
| **User Journey** | После изменения AI/Orchestrator/KB конфигурации старые кэшированные ответы не возвращаются. |
| **Preconditions** | Выполнены STU-08 и ADM-05/ADM-06. |
| **Steps** | 1. Задать вопрос, убедиться в кэше. <br>2. Изменить конфигурацию. <br>3. Повторить тот же вопрос. |
| **Expected Result** | Ответ пересчитан, не из кэша. `cache_hit=false`. |
| **Backend / Data Checks** | Response cache cleared. |
| **Status** | |
| **Notes** | |

### 3.2 Реальный IP студента в логах

| Поле | Значение |
|---|---|
| **ID** | CROSS-02 |
| **User Journey** | Запрос студента из внешней сети не логируется с Docker-internal IP. |
| **Preconditions** | Доступ к prod Web UI из внешней сети. |
| **Steps** | 1. Зайти на `curator.alex-n8n.site` с публичного IP. <br>2. Задать вопрос. <br>3. Проверить `audit_logs.ip_address`. |
| **Expected Result** | `ip_address` — публичный IP пользователя, а не `172.21.0.x`. |
| **Backend / Data Checks** | `audit_logs.ip_address` не начинается с `172.21.` или `10.` или `192.168.`. |
| **Status** | |
| **Notes** | |

### 3.3 Неверный токен Admin Console

| Поле | Значение |
|---|---|
| **ID** | NEG-01 |
| **User Journey** | Попытка входа с неверным токеном. |
| **Preconditions** | AC открыт. |
| **Steps** | 1. Ввести заведомо неверный токен. <br>2. Нажать «Войти». |
| **Expected Result** | Ошибка входа, Dashboard не открывается, HTTP 401/403. |
| **Backend / Data Checks** | В `audit_logs` нет новой записи (аутентификация не прошла). |
| **Status** | |
| **Notes** | |

### 3.4 Неподдерживаемый файл в KB

| Поле | Значение |
|---|---|
| **ID** | NEG-02 |
| **User Journey** | Попытка загрузить неподдерживаемый формат. |
| **Preconditions** | AC открыт, раздел KB. |
| **Steps** | 1. Нажать «Загрузить версию». <br>2. Выбрать файл `.bin`. <br>3. Сохранить. |
| **Expected Result** | UI показывает ошибку 415 Unsupported Media Type, документ не создан. |
| **Backend / Data Checks** | В `audit_logs` нет записи `create` (операция не выполнена). |
| **Status** | |
| **Notes** | |

---

## Раздел 4. Deployment Validation

| ID | Проверка | Ожидаемый результат | Статус |
|---|---|---|---|
| DEP-01 | `docker compose ps` | Все контейнеры healthy / running | |
| DEP-02 | `curl https://curator-api.alex-n8n.site/health` | `{"status":"ok"}` | |
| DEP-03 | `curl https://curator.alex-n8n.site` | HTML 200 | |
| DEP-04 | `curl https://curator-admin.alex-n8n.site` | HTML 200 | |
| DEP-05 | `curl https://lms.alex-n8n.site/login/index.php` | HTML 200 | |
| DEP-06 | SSL-сертификаты валидны | Браузер не показывает предупреждение | |

---

## Раздел 5. Phase 2 — запланированные сценарии

После реализации соответствующих фич добавить сюда:

| ID | Сценарий | Блокирующая фича |
|---|---|---|
| PH2-01 | Просмотр Analytics Dashboard: total_requests, intent_distribution, latency | Sprint E1 |
| PH2-02 | Экспорт Business Report: unanswered questions, KB gaps | Sprint E2 |
| PH2-03 | Read-only demo-вход в Admin Console без возможности изменений | Sprint A2/A3 |
| PH2-04 | Safe demo mode на Web UI: rate limit, квота сессии, капча | Sprint F |
| PH2-05 | Автоматизированный Playwright-прогон всех сценариев Phase 1 | Инфраструктура |

---

## Связь с другими документами

- `docs/ORCHESTRATOR_E2E_CHECKLIST.md` — детальные проверки оркестратора, cross-reference для STU-03..STU-07 и ADM-06.
- `docs/TESTING_CONTRACT.md` — автоматизированные backend-тесты.
- `docs/DEPLOYMENT_GUIDE.md` — инструкции для DEP-01..DEP-06.
- `docs/E2E_TEST_PLAN.md` — стратегия, частота, инструменты, критерии приёмки.

---

## История изменений

| Дата | Версия | Изменение |
|---|---|---|
| 2026-08-04 | 1.0 | Начальная версия Phase 1. |
