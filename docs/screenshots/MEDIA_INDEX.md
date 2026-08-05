# AI Curator — каталог медиаматериалов

**Проект:** ai-curator  
**Дата:** 2026-08-05  
**Статус:** В процессе наполнения

---

## 1. Правила нейминга

Формат: `AIC_{CATEGORY}_{DESCRIPTION}.{ext}`

| Категория | Назначение | Пример |
|-----------|------------|--------|
| `web` | Веб-интерфейс студента | `AIC_web_chat_basic.png` |
| `admin` | Консоль администратора AI Curator | `AIC_admin_dashboard.png` |
| `lms` | Moodle LMS | `AIC_lms_teacher_assignment.png` |
| `arch` | Архитектурные схемы | `AIC_architecture_mermaid.png` |
| `demo` | Демонстрационные GIF/видео | `AIC_demo_walkthrough.gif` |

---

## 2. Каталог изображений

| ID | Файл | Категория | Назначение | Используется в |
|----|------|-----------|------------|----------------|
| IMG-001 | `AIC_web_role_selector.png` | web | Landing page выбора demo-роли: `active_student`, `late_student`, `new_student` | README, SYSTEM_DEMO, USER_GUIDE |
| IMG-002 | `AIC_web_chat_basic.png` | web | Диалог студента: вопрос про дедлайн `PE07. Chain-of-thought`, ответ с LMS-ссылкой | README, SYSTEM_DEMO, USER_GUIDE |
| IMG-003 | `AIC_web_sources_expanded.png` | web | Ответ на учебный вопрос с новыми карточками источников KB и LMS | SYSTEM_DEMO, USER_GUIDE, E2E_SCENARIOS |
| IMG-004 | `AIC_web_difficulty_toggle.png` | web | Учебный диалог с активным переключателем сложности `Базовый / Углублённый`. Вопрос «Что такое промпт?», ответ с карточками источников KB | USER_GUIDE, SYSTEM_DEMO |
| IMG-005 | `AIC_web_demo_badge.png` | web | Demo-режим: бейдж с оставшимися запросами, таймер сессии, источники KB | SYSTEM_DEMO, USER_GUIDE |
| IMG-006 | `AIC_web_no_answer.png` | web | Сценарий «вопрос без данных»: запрос пароля Moodle и fallback-ответ | USER_GUIDE, FAQ |
| IMG-010 | `AIC_admin_login.png` | admin | Экран входа с Bearer-токеном и кнопка demo-режима | ADMIN_GUIDE, SYSTEM_DEMO |
| IMG-011 | `AIC_admin_dashboard.png` | admin | Панель состояния: health сервисов, KPI за 24ч, активность по интентам, состояние KB | README, SYSTEM_DEMO, ADMIN_GUIDE |
| IMG-012 | `AIC_admin_kb_list.png` | admin | **Общий вид панели База знаний**: слева список документов, справа детальная карточка выбранного документа `PE07. Chain-of-thought` | SYSTEM_DEMO, ADMIN_GUIDE, CURATOR_GUIDE |
| IMG-013 | `AIC_admin_kb_detail.png` | admin | **Фрагмент детальной карточки документа KB**: метаданные, версии, чанки, lifecycle | ADMIN_GUIDE, CURATOR_GUIDE |
| IMG-014 | `AIC_admin_kb_upload.png` | admin | Форма загрузки нового документа в Базе знаний: метаданные и выбор файла `faq-ai-terminology.md` | CURATOR_GUIDE, ADMIN_GUIDE |
| IMG-015 | `AIC_admin_ai_config.png` | admin | AI & Retrieval Configuration: LLM-провайдеры, RAG-параметры, system prompt | ADMIN_GUIDE |
| IMG-016 | `AIC_admin_orchestrator.png` | admin | Настройки оркестратора: классификация интентов, маршрутизация, fallback-ответы | ADMIN_GUIDE, ORCHESTRATOR_USER_GUIDE |
| IMG-017 | `AIC_admin_analytics.png` | admin | Панель аналитики: распределение запросов, источники ответов, latency | SYSTEM_DEMO, ADMIN_GUIDE |
| IMG-018 | `AIC_admin_reports.png` | admin | Управленческие отчёты: качество ответов, покрытие KB, вопросы без ответа | SYSTEM_DEMO, ADMIN_GUIDE |
| IMG-019 | `AIC_admin_operational_logs.png` | admin | Операционные логи: список запросов с фильтрами и детализация pipeline | ADMIN_GUIDE, OPERATIONS |
| IMG-020 | `AIC_admin_dialog_sessions.png` | admin | Диалоговые сессии: операционная консоль диалогов с таймлайном шагов | ADMIN_GUIDE |
| IMG-021 | `AIC_admin_audit.png` | admin | Журнал аудита: административные события и детали выбранной записи | ADMIN_GUIDE, SYSTEM_DEMO |
| IMG-022 | `AIC_admin_export_csv.png` | admin | Операционные логи: кнопка `Экспорт CSV` и детальная карточка запроса с таймлайном pipeline | ADMIN_GUIDE, OPERATIONS |
| IMG-030 | `AIC_lms_admin_course_structure.png` | lms | Структура курса «Промпт-инжиниринг» в Moodle: модули и темы | SYSTEM_DEMO, E2E_SCENARIOS, CURATOR_GUIDE |
| IMG-031 | `AIC_lms_teacher_assignment.png` | lms | Преподаватель создаёт задание `PE07. Chain-of-thought`, дедлайн `2026-08-24 15:59` | E2E_SCENARIOS, SYSTEM_DEMO |
| IMG-032 | `AIC_lms_teacher_deadline.png` | lms | Настройки задания `PE07. Chain-of-thought`: срок сдачи и тип ответа | E2E_SCENARIOS |
| IMG-033 | `AIC_lms_webservice_token.png` | lms | Управление ключами веб-служб Moodle: токен `AI Curator Read-Only Token` | ADMIN_GUIDE, DEPLOYMENT_GUIDE |
| IMG-034 | `AIC_lms_student_course_view.png` | lms | Студент в Moodle: курс «Claude Code...», модули, оценки | SYSTEM_DEMO, E2E_SCENARIOS |
| IMG-040 | `AIC_architecture_mermaid.png` | arch | Архитектурная схема (опционально, если Mermaid на GitHub рендерится плохо) | README, SYSTEM_DEMO |
| IMG-041 | `AIC_demo_walkthrough.gif` | demo | Demo walkthrough 15 сек (опционально) | README, SYSTEM_DEMO |

---

## 3. Единый демо-контекст для скриншотов

| Параметр | Значение |
|---|---|
| Проект | AI Curator |
| Demo-роль | `active_student` |
| Курсы | `Промпт-инжиниринг` (course_id: 4), `Claude Code: от знакомства до автоматизации` (course_id: 3) |
| Задание с дедлайном | `PE07. Chain-of-thought` |
| Дедлайн | `2026-08-24 15:59` |
| LLM | `gpt-4o-mini-2024-07-18` |
| Embedding | `text-embedding-3-small` |
| Диапазон аналитики | `2026-08-01 – 2026-08-05` |
| Demo-лимит | `20` запросов на сессию |

---

Переименование файлов не требуется: имена соответствуют плану документации. Если содержимое скриншота отличается от буквального прочтения имени, расхождение отражается в описании каталога.

## 4. Правила добавления новых скриншотов

1. Использовать схему нейминга `AIC_{CATEGORY}_{DESCRIPTION}.png`.
2. Добавить строку в таблицу каталога.
3. Указать, в каких документах используется.
4. Не добавлять изображения без явного назначения.
5. Скриншоты UI/API только; архитектурные схемы — в Mermaid внутри Markdown.
