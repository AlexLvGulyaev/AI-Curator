# AI Curator — руководство администратора

**Проект:** ai-curator  
**Дата:** 2026-08-05  
**URL:** `https://curator-admin.alex-n8n.site`

---

## 1. Назначение

Это руководство для **администратора AI Curator** — человека, который управляет Knowledge Base, AI-конфигурацией, аналитикой, мониторингом и безопасностью системы.

Администратор AI Curator не управляет учебным процессом в LMS. Курсы, задания, дедлайны и оценки остаются в ведении LMS.

---

## 2. Вход в Admin Console

1. Перейдите по адресу `https://curator-admin.alex-n8n.site`.
2. Введите Bearer-токен из переменной окружения `ADMIN_CONSOLE_TOKEN`.
3. Нажмите **Войти**.

Токен хранится в `localStorage` браузера и передаётся в заголовке `Authorization: Bearer <token>`.

![Экран входа в Admin Console с Bearer-токеном](screenshots/AIC_admin_login.png)

---

## 3. Dashboard

Dashboard показывает общее состояние системы:

- количество документов Knowledge Base;
- активная AI-конфигурация;
- статус LLM-провайдера;
- краткая аналитика запросов.

![Dashboard: health сервисов и KPI](screenshots/AIC_admin_dashboard.png)

---

## 4. Knowledge Base

Раздел **Knowledge Base → Документы** — трёхпанельная операционная консоль:

- **Список документов** слева — фильтры, поиск, статусы.
- **Детальная карточка** по центру — метаданные, версии, чанки.
- **Жизненный цикл** справа — timeline событий обработки.

![Панель Knowledge Base: список документов и детальная карточка](screenshots/AIC_admin_kb_list.png)

![Детальная карточка документа: метаданные, версии, чанки](screenshots/AIC_admin_kb_detail.png)

Для загрузки нового документа нажмите **Загрузить файл**, заполните метаданные и выберите файл.

![Форма загрузки документа в Knowledge Base](screenshots/AIC_admin_kb_upload.png)

---

## 5. AI & Retrieval Configuration

В разделе **AI Config** управляются:

- `system_prompt` — роль и правила AI Curator;
- модель LLM, temperature, max_tokens;
- `top_k_retrieval` и `rag_distance_threshold`;
- инструкции для уровней Beginner / Advanced;
- few-shot примеры;
- правила вывода и текст отказа.

![AI & Retrieval Configuration](screenshots/AIC_admin_ai_config.png)

Каждая новая версия конфигурации создаётся неактивной. Активация производится отдельной кнопкой.

---

## 6. Orchestrator Configuration

Orchestrator определяет:

- интент-классификацию по ключевым словам;
- source routing: LMS, Knowledge Base, оба источника, strict_course;
- token-бюджеты по интентам;
- fallback-сообщения;
- размеры LMS-контекста.

![Orchestrator Configuration: интенты, маршрутизация, fallback](screenshots/AIC_admin_orchestrator.png)

Подробнее см. [`ORCHESTRATOR_USER_GUIDE.md`](ORCHESTRATOR_USER_GUIDE.md).

---

## 7. Analytics и Reports

### Analytics Dashboard

- KPI за период;
- latency histogram;
- распределение источников ответов;
- популярные темы;
- динамика по курсам.

![Analytics Dashboard: распределение запросов и источники ответов](screenshots/AIC_admin_analytics.png)

### Business Reports / Quality Reports

- качество ответов;
- вопросы без ответа;
- гэпы Knowledge Base;
- кандидаты на расширение KB;
- CSV export.

![Business Reports: качество ответов и покрытие KB](screenshots/AIC_admin_reports.png)

---

## 8. Operational Logs и Dialog Sessions

### Operational Logs

Operational Logs показывают каждый запрос студента с фильтрами по роли, источнику, интенту, статусу и дате.

![Operational Logs: список запросов с фильтрами](screenshots/AIC_admin_operational_logs.png)

### Dialog Sessions

Dialog Sessions показывают полный timeline обработки запроса: получение запроса → классификация intent → embedding → Chroma search → RAG-постобработка → генерация LLM → валидация → ответ.

![Dialog Sessions: таймлайн обработки запроса](screenshots/AIC_admin_dialog_sessions.png)

---

## 9. Audit Log

Audit Log фиксирует изменяющие действия в системе:

- активация AI-конфигурации;
- публикация документа KB;
- обновление Orchestrator-конфигурации;
- chat-запросы студентов (с `session_id`, `ip_address`).

![Audit Log: журнал административных событий](screenshots/AIC_admin_audit.png)

---

## 10. Экспорт логов

В разделах Operational Logs, Audit Log и Dialog Sessions доступен экспорт в CSV.

![Operational Logs: кнопка Экспорт CSV и детальная карточка запроса](screenshots/AIC_admin_export_csv.png)

Политика ротации:

- hot logs хранятся 30 дней, затем архивируются в `ARCHIVE_DIR`;
- LLM traces хранятся 7 дней;
- архивы — gzip JSON Lines.

Подробнее см. [`OPERATIONS.md`](OPERATIONS.md) раздел 9.

---

## 11. Интеграция с LMS

AI Curator читает данные учебного процесса из Moodle LMS через read-only Web Services token.

### Требования к LMS

1. Включены Moodle Web Services.
2. Создан read-only токен с правами на чтение курсов, заданий, пользователей, прогресса.
3. Курс, модули и задания заведены в LMS.

### Где взять токен

Moodle: **Site administration → Server → Web services → Manage tokens**.

![Moodle: управление Web service token](screenshots/AIC_lms_webservice_token.png)

Токен указывается в переменной окружения `LMS_API_TOKEN`. Никогда не коммитьте токен в репозиторий.

---

## 12. Demo-режим Admin Console

Для публичных демонстраций можно использовать `ADMIN_CONSOLE_DEMO_TOKEN`:

- demo-роль имеет доступ только на чтение;
- кнопки мутаций заблокированы;
- в интерфейсе отображается бейдж demo-режима.

---

## 13. Типовые проблемы

| Симптом | Возможная причина | Решение |
|---|---|---|
| Ответы AI не используют новый материал | Документ не опубликован / не переиндексирован | Проверить статус документа в Knowledge Base и запустить переиндексацию |
| Долгие ответы | Высокое значение `top_k` или большой контекст | Уменьшить `top_k`, проверить token-бюджеты в Orchestrator |
| Организационные ответы не работают | LMS API недоступен или токен истёк | Проверить `LMS_API_TOKEN` и health LMS в Monitoring |
| Пустой Audit Log | Нет изменяющих действий | Выполнить любую мутацию или chat-запрос |

---

## Связанные документы

- [`docs/ADMIN_CONSOLE.md`](ADMIN_CONSOLE.md) — component reference Admin Console.
- [`docs/OPERATIONS.md`](OPERATIONS.md) — эксплуатация, retention, KB workflow.
- [`docs/ORCHESTRATOR_USER_GUIDE.md`](ORCHESTRATOR_USER_GUIDE.md) — настройка Orchestrator.
- [`docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание и env vars.
