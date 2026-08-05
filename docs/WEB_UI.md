# Web UI AI Curator

**Проект:** ai-curator  
**Дата:** 2026-07-29  
**URL:** `https://ai-curator.example.com`

---

## Обзор

Web UI AI Curator — отдельный публичный frontend-сервис для студентов. Он предоставляет чат с AI-ассистентом, позволяет задавать организационные и учебные вопросы, получать ответы с источниками и выбирать уровень сложности.

Web UI не встраивается в Moodle и не дублирует административные функции LMS. Он является публичным интерфейсом к Backend AI Curator.

---

## Стек

| Компонент | Технология |
|-----------|------------|
| Библиотека UI | React 18 |
| Сборщик | Vite 5 |
| Стили | Tailwind CSS 3 |
| Шрифты | Inter (body), Outfit (display) |
| HTTP-клиент | fetch |
| Production сервер | nginx |
| Контейнеризация | Docker + Docker Compose |

---

## Структура каталога

```
web-ui/
├── Dockerfile
├── nginx.conf
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── vite.config.js
├── index.html
└── src/
    ├── main.jsx
    ├── App.jsx
    ├── index.css
    ├── api/
    │   └── backend.js
    ├── components/
    │   ├── Chat.jsx
    │   ├── DifficultyToggle.jsx
    │   ├── Message.jsx
    │   └── RoleSelector.jsx
    └── hooks/
        └── useChat.js
```

---

## Архитектура

### Компоненты

- **App** — корневой компонент, управляет выбранной ролью через `localStorage`.
- **RoleSelector** — экран выбора демо-роли.
- **Chat** — основной экран чата: заголовок, список сообщений, поле ввода.
- **Message** — отображение сообщения пользователя или ответа AI с источниками.
- **DifficultyToggle** — переключатель уровня сложности ответа.

### Хуки

- **useChat** — состояние чата, отправка сообщений, интент-детекция, вызов backend API.

### API client

- **backend.js** — функции для `health`, `courses`, `deadlines`, `progress`, `rag/search`.

---

## Демо-роли

| Роль | Идентификатор | Описание |
|------|---------------|----------|
| Активный студент | `active_student` | Вовлечён в курс, сдаёт вовремя, интересует углубление |
| Отстающий студент | `late_student` | Пропустил дедлайны, нуждается в плане наверстания |
| Новый студент | `new_student` | Только начинает курс, нуждается в ориентации |

Роль сохраняется в `localStorage` и влияет на сценарии, отображаемые в чате. В текущей версии роль используется для персонализации ответов по дедлайнам и прогрессу.

---

## Потоки вопросов

### Организационные вопросы

Ключевые слова: дедлайн, срок, сдача, задание, когда, прогресс, оценка.

Web UI вызывает:
- `GET /api/v1/courses/{course_id}/deadlines`
- `GET /api/v1/me/progress`

Ответ формируется из ближайших дедлайнов и статуса прохождения курса. Источники — ссылки на задания в LMS.

### Учебные вопросы

Все остальные вопросы направляются в RAG:
- `POST /api/v1/rag/search`

В запрос передаются `course_id` и `difficulty`. Ответ содержит текст релевантного фрагмента и ссылки на материалы Knowledge Base.

---

## Цветовая система

Web UI использует светлую тему с CSS-переменными, вдохновлённую подходом `ai-portfolio/admin` и акцентами из `prompt-review`:

- **Основной фон:** `#f8fafc`
- **Поверхность:** `#ffffff`
- **Основной текст:** `#0f172a`
- **Primary accent (violet):** `#7c3aed`
- **Secondary accent (teal для AI):** `#14b8a6`
- **Радиус:** `10px`
- **Тень:** `0 4px 12px rgba(15, 23, 42, 0.08)`

---

## Переменные окружения

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `VITE_API_BASE_URL` | `https://ai-curator-api.example.com` | Базовый URL backend API |

---

## Запуск в development

```bash
cd web-ui
npm install
npm run dev
```

Vite проксирует `/api` на `https://ai-curator-api.example.com`.

---

## Production

```bash
cd web-ui
npm run build
cd ..
docker compose up -d ai-curator-web-ui
```

---

## CORS

Backend разрешает запросы с `WEB_UI_URL` и `ADMIN_CONSOLE_URL`. Для production убедитесь, что `.env` содержит:

```env
WEB_UI_URL=https://ai-curator.example.com
ADMIN_CONSOLE_URL=https://ai-curator-admin.example.com
```

---

## Связанные документы

- [📖 `docs/USER_GUIDE.md`](USER_GUIDE.md) — руководство студента по Web UI.
- [🏗️ `docs/ARCHITECTURE.md`](ARCHITECTURE.md) — место Web UI в архитектуре системы.
- [🚀 `docs/DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) — развёртывание и переменные окружения.

---

## История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-07-29 | 1.0 | Создан документ |
| 2026-08-05 | 1.1 | Актуализировано под demo-режим, safe mode, markdown-ответы, историю диалога, feedback |
