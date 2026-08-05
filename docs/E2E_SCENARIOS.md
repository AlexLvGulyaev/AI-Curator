# AI Curator — сквозные бизнес-сценарии

**Проект:** ai-curator  
**Дата:** 2026-08-05

---

## 1. Организационный вопрос

**Участники:** студент, AI Curator, Moodle LMS.

**Цель:** узнать дедлайн по заданию.

**Шаги:**

1. Студент открывает Web UI AI Curator.
2. Выбирает demo-роль `active_student`.
3. Вводит вопрос: `Когда дедлайн по заданию PE07?`
4. Backend классифицирует запрос как организационный.
5. Через LMS Adapter Backend получает задание и дедлайн из Moodle.
6. Backend формирует ответ: `Дедлайны заданий: «ДЗ: PE07. Chain-of-thought»: 2026-08-24.`
7. Студент видит ответ и ссылку на задание в LMS.

**Ожидаемый результат:** точный ответ с источником `LMS`.

**Скриншоты:** [`AIC_web_chat_basic.png`](screenshots/AIC_web_chat_basic.png), [`AIC_lms_teacher_deadline.png`](screenshots/AIC_lms_teacher_deadline.png).

---

## 2. Учебный вопрос

**Участники:** студент, AI Curator, Knowledge Base.

**Цель:** понять тему курса.

**Шаги:**

1. Студент выбирает уровень сложности `Базовый`.
2. Задаёт вопрос: `Что такое промпт?`
3. Backend определяет курс, модуль, тему.
4. Выполняется retrieval по Knowledge Base.
5. Backend формирует RAG-контекст и вызывает LLM.
6. Ответ содержит объяснение и карточки источников: `PE01. Что такое промпт`, `CC05. Структура эффективного промпта`, `ДЗ: PE01. Что такое промпт`.

**Ожидаемый результат:** содержательный ответ с источниками `Knowledge Base`.

**Скриншоты:** [`AIC_web_sources_expanded.png`](screenshots/AIC_web_sources_expanded.png), [`AIC_web_difficulty_toggle.png`](screenshots/AIC_web_difficulty_toggle.png).

---

## 3. Смешанный вопрос

**Участники:** студент, AI Curator, LMS, Knowledge Base.

**Цель:** получить персональную рекомендацию перед заданием.

**Шаги:**

1. Студент спрашивает: `Что мне повторить перед заданием PE07?`
2. Backend получает из LMS: задание, дедлайн, прогресс студента.
3. Backend получает из Knowledge Base: связанные лекции и методички.
4. Backend объединяет контекст и формирует персональную рекомендацию.
5. Студент видит ответ с источниками LMS + Knowledge Base.

**Ожидаемый результат:** персональная рекомендация с двумя типами источников.

**Скриншоты:** [`AIC_web_sources_expanded.png`](screenshots/AIC_web_sources_expanded.png).

---

## 4. Управление Knowledge Base

**Участники:** методист, Admin Console AI Curator.

**Цель:** добавить новый учебный материал.

**Шаги:**

1. Методист открывает Admin Console.
2. Переходит в **Knowledge Base → Документы**.
3. Нажимает **Загрузить файл**.
4. Заполняет название `PE08. Zero-shot и few-shot`, тип `lecture`, курс/модуль/тему.
5. Загружает файл и сохраняет документ.
6. Выбирает документ и нажимает **Переиндексировать**.
7. После успешной индексации включает публикацию.

**Ожидаемый результат:** документ доступен для ответов студентам.

**Скриншоты:** [`AIC_admin_kb_upload.png`](screenshots/AIC_admin_kb_upload.png), [`AIC_admin_kb_detail.png`](screenshots/AIC_admin_kb_detail.png).

---

## 5. Контроль качества

**Участники:** администратор AI Curator, Admin Console.

**Цель:** проанализировать вопросы студентов и улучшить Knowledge Base.

**Шаги:**

1. Администратор открывает **Reports → Quality Reports**.
2. Видит темы с низким покрытием KB.
3. Открывает **Knowledge Base** и добавляет недостающий материал.
4. Переиндексирует и публикует документ.
5. Проверяет в Web UI, что ответы теперь используют новый материал.

**Ожидаемый результат:** снижение количества вопросов без ответа.

**Скриншоты:** [`AIC_admin_reports.png`](screenshots/AIC_admin_reports.png), [`AIC_admin_analytics.png`](screenshots/AIC_admin_analytics.png).

---

## 6. Настройка учебного процесса в LMS

**Участники:** администратор LMS, преподаватель, Moodle.

**Цель:** подготовить структуру курса, чтобы AI Curator мог отвечать на организационные вопросы.

**Шаги:**

1. Администратор LMS создаёт курс `Промпт-инжиниринг` и модули.
2. Преподаватель добавляет задания с дедлайнами.
3. Преподаватель зачисляет студентов.
4. Администратор LMS создаёт read-only Web Services token для AI Curator.
5. Администратор AI Curator добавляет `LMS_API_TOKEN` в `.env`.

**Ожидаемый результат:** AI Curator читает курсы, задания, дедлайны и прогресс из Moodle.

**Скриншоты:** [`AIC_lms_admin_course_structure.png`](screenshots/AIC_lms_admin_course_structure.png), [`AIC_lms_teacher_assignment.png`](screenshots/AIC_lms_teacher_assignment.png), [`AIC_lms_teacher_deadline.png`](screenshots/AIC_lms_teacher_deadline.png), [`AIC_lms_webservice_token.png`](screenshots/AIC_lms_webservice_token.png).

---

## Связанные документы

- [`docs/SYSTEM_DEMO.md`](SYSTEM_DEMO.md) — скриншоты и live demo.
- [`docs/USER_GUIDE.md`](USER_GUIDE.md) — руководство студента.
- [`docs/ADMIN_GUIDE.md`](ADMIN_GUIDE.md) — руководство администратора.
- [`docs/CURATOR_GUIDE.md`](CURATOR_GUIDE.md) — руководство методиста.
