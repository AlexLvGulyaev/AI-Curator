# AI Curator — каталог медиаматериалов

**Проект:** ai-curator  
**Дата:** 2026-08-05  
**Статус:** В процессе наполнения

---

## 1. Правила нейминга

Формат: `AIC_{CATEGORY}_{DESCRIPTION}.{ext}`

| Категория | Назначение | Пример |
|-----------|------------|--------|
| `web` | Web UI студента | `AIC_web_chat_basic.png` |
| `admin` | Admin Console AI Curator | `AIC_admin_dashboard.png` |
| `lms` | Moodle LMS | `AIC_lms_teacher_assignment.png` |
| `arch` | Архитектурные схемы | `AIC_architecture_mermaid.png` |
| `demo` | Демонстрационные GIF/видео | `AIC_demo_walkthrough.gif` |

---

## 2. Каталог изображений

| ID | Файл | Категория | Назначение | Используется в |
|----|------|-----------|------------|----------------|
| IMG-001 | `AIC_web_role_selector.png` | web | Экран выбора demo-роли | README, SYSTEM_DEMO, USER_GUIDE |
| IMG-002 | `AIC_web_chat_basic.png` | web | Обычный диалог студента | README, SYSTEM_DEMO, USER_GUIDE |
| IMG-003 | `AIC_web_sources_expanded.png` | web | Ответ с развёрнутыми источниками | SYSTEM_DEMO, USER_GUIDE, E2E_SCENARIOS |
| IMG-004 | `AIC_web_difficulty_toggle.png` | web | Переключатель Beginner / Advanced | USER_GUIDE, SYSTEM_DEMO |
| IMG-005 | `AIC_web_demo_badge.png` | web | Demo-режим: бейдж, квоты, таймер | SYSTEM_DEMO, USER_GUIDE |
| IMG-006 | `AIC_web_no_answer.png` | web | Состояние «не хватает данных» | USER_GUIDE, FAQ |
| IMG-010 | `AIC_admin_login.png` | admin | Экран входа с Bearer-токеном | ADMIN_GUIDE, SYSTEM_DEMO |
| IMG-011 | `AIC_admin_dashboard.png` | admin | Dashboard с KPI | README, SYSTEM_DEMO, ADMIN_GUIDE |
| IMG-012 | `AIC_admin_kb_list.png` | admin | Список документов Knowledge Base | SYSTEM_DEMO, ADMIN_GUIDE, CURATOR_GUIDE |
| IMG-013 | `AIC_admin_kb_detail.png` | admin | Детальная карточка документа | ADMIN_GUIDE, CURATOR_GUIDE |
| IMG-014 | `AIC_admin_kb_upload.png` | admin | Модальное окно загрузки документа | CURATOR_GUIDE |
| IMG-015 | `AIC_admin_ai_config.png` | admin | AI & Retrieval Configuration | ADMIN_GUIDE |
| IMG-016 | `AIC_admin_orchestrator.png` | admin | Orchestrator Configuration | ADMIN_GUIDE, ORCHESTRATOR_USER_GUIDE |
| IMG-017 | `AIC_admin_analytics.png` | admin | Analytics Dashboard | SYSTEM_DEMO, ADMIN_GUIDE |
| IMG-018 | `AIC_admin_reports.png` | admin | Business Reports / Quality Reports | SYSTEM_DEMO, ADMIN_GUIDE |
| IMG-019 | `AIC_admin_operational_logs.png` | admin | Operational Logs с фильтрами | ADMIN_GUIDE, OPERATIONS |
| IMG-020 | `AIC_admin_dialog_sessions.png` | admin | Dialog Sessions / timeline | ADMIN_GUIDE |
| IMG-021 | `AIC_admin_audit.png` | admin | Audit Log | ADMIN_GUIDE, SYSTEM_DEMO |
| IMG-022 | `AIC_admin_export_csv.png` | admin | Кнопки экспорта CSV логов | ADMIN_GUIDE, OPERATIONS |
| IMG-030 | `AIC_lms_admin_course_structure.png` | lms | Структура курса в Moodle | SYSTEM_DEMO, E2E_SCENARIOS, CURATOR_GUIDE |
| IMG-031 | `AIC_lms_teacher_assignment.png` | lms | Создание задания с дедлайном | E2E_SCENARIOS, SYSTEM_DEMO |
| IMG-032 | `AIC_lms_teacher_deadline.png` | lms | Вид задания со сроком сдачи | E2E_SCENARIOS |
| IMG-033 | `AIC_lms_webservice_token.png` | lms | Web service token в Moodle | ADMIN_GUIDE, DEPLOYMENT_GUIDE |
| IMG-034 | `AIC_lms_student_course_view.png` | lms | Студент в Moodle | SYSTEM_DEMO, E2E_SCENARIOS |
| IMG-040 | `AIC_architecture_mermaid.png` | arch | Архитектурная схема (опционально) | README, SYSTEM_DEMO |
| IMG-041 | `AIC_demo_walkthrough.gif` | demo | Demo walkthrough 15 сек | README, SYSTEM_DEMO |

---

## 3. Единый демо-контекст для скриншотов

Все скриншоты делаются в рамках одного сценария:

| Параметр | Значение |
|---|---|
| Курс | `AI Skills Lab` |
| Студент | `Алексей Иванов` |
| Demo-роль | `active_student` |
| Задание | `PE07. Chain-of-thought` |
| Дедлайн | `2026-08-15 23:59` |
| LLM | `gpt-4o-mini-2024-07-18` |
| Embedding | `text-embedding-3-small` |
| Диапазон аналитики | `2026-08-01 – 2026-08-05` |

---

## 4. Правила добавления новых скриншотов

1. Использовать схему нейминга `AIC_{CATEGORY}_{DESCRIPTION}.png`.
2. Добавить строку в таблицу каталога.
3. Указать, в каких документах используется.
4. Не добавлять изображения без явного назначения.
5. Скриншоты UI/API только; архитектурные схемы — в Mermaid внутри Markdown.
