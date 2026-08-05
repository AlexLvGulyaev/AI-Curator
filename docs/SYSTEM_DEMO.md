# AI Curator — демонстрация системы

**Проект:** ai-curator  
**Дата:** 2026-08-05  
**Live Demo:** `https://curator.alex-n8n.site`

---

## 1. Как открыть live demo

1. Перейдите по адресу `https://curator.alex-n8n.site`.
2. Выберите одну из demo-ролей: `active_student`, `late_student`, `new_student`.
3. Задайте вопрос AI Curator.

Для публичных демонстраций включён safe demo mode: квота запросов, rate limit и таймер сессии.

---

## 2. Web UI студента

### Выбор demo-роли

![Выбор demo-роли](screenshots/AIC_web_role_selector.png)

### Диалог с AI-куратором

![Пример диалога](screenshots/AIC_web_chat_basic.png)

### Ответ с источниками

![Источники ответа](screenshots/AIC_web_sources_expanded.png)

### Переключатель уровня сложности

![Уровень сложности](screenshots/AIC_web_difficulty_toggle.png)

### Demo-режим

![Demo-режим](screenshots/AIC_web_demo_badge.png)

---

## 3. Admin Console

### Dashboard

![Dashboard](screenshots/AIC_admin_dashboard.png)

### Knowledge Base

![Список документов](screenshots/AIC_admin_kb_list.png)

![Детальная карточка документа](screenshots/AIC_admin_kb_detail.png)

### AI Configuration

![AI Configuration](screenshots/AIC_admin_ai_config.png)

### Orchestrator Configuration

![Orchestrator](screenshots/AIC_admin_orchestrator.png)

### Analytics

![Analytics](screenshots/AIC_admin_analytics.png)

### Business Reports

![Business Reports](screenshots/AIC_admin_reports.png)

### Audit Log

![Audit Log](screenshots/AIC_admin_audit.png)

---

## 4. Moodle LMS — Source of Truth учебного процесса

### Структура курса

![Структура курса](screenshots/AIC_lms_admin_course_structure.png)

### Задание с дедлайном

![Создание задания](screenshots/AIC_lms_teacher_assignment.png)

![Дедлайн в задании](screenshots/AIC_lms_teacher_deadline.png)

### Студент в Moodle

![Студент в Moodle](screenshots/AIC_lms_student_course_view.png)

---

## 5. Видео-обзор

Если подготовлен, здесь будет короткий GIF или видео walkthrough.

**Плейсхолдер:** `[Demo walkthrough GIF — 15 сек]`

Сценарий walkthrough:

1. Выбор demo-роли `active_student`.
2. Вопрос: `Когда дедлайн по заданию PE07?`
3. Ответ с источником `LMS`.
4. Переключение уровня сложности.
5. Учебный вопрос с источниками `Knowledge Base`.

---

## 6. Сценарии

Подробные бизнес-сценарии описаны в [`docs/E2E_SCENARIOS.md`](E2E_SCENARIOS.md).

---

## Связанные документы

- [`README.md`](../README.md) — главная страница проекта.
- [`docs/BUSINESS_VALUE.md`](BUSINESS_VALUE.md) — бизнес-ценность.
- [`docs/USER_GUIDE.md`](USER_GUIDE.md) — как пользоваться Web UI.
