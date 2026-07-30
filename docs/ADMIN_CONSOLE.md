# ADMIN_CONSOLE.md — AI Curator Admin Console

**Проект:** ai-curator  
**Версия:** 1.0  
**Дата:** 2026-07-30  
**Статус:** Актуален для Дня 6

---

## 1. Назначение

Admin Console AI Curator — отдельный публичный веб-интерфейс для администраторов и методистов. Позволяет управлять Knowledge Base, конфигурацией AI, просматривать аналитику и мониторинг.

URL: `https://curator-admin.alex-n8n.site`

---

## 2. Стек

- React 18
- Vite 5
- Tailwind CSS 3
- Recharts (графики аналитики)
- react-markdown + rehype-sanitize (рендеринг markdown)
- nginx (статический хостинг)
- Docker + Docker Compose

---

## 3. Аутентификация

Admin Console использует статический Bearer-токен из переменной окружения `ADMIN_CONSOLE_TOKEN`.

При входе токен сохраняется в `localStorage` и передаётся в заголовке `Authorization: Bearer <token>` для всех запросов к `/api/v1/admin/*`.

Если `ADMIN_CONSOLE_TOKEN` не задан или равен плейсхолдеру, административные endpoints не требуют авторизации (не рекомендуется для production).

---

## 4. Структура компонентов

| Компонент | Размещение | Назначение |
|-----------|------------|------------|
| `Login.jsx` | `src/components/Login.jsx` | Ввод Bearer-токена |
| `Sidebar.jsx` | `src/components/Sidebar.jsx` | Навигация |
| `Dashboard.jsx` | `src/components/Dashboard.jsx` | Панель состояния системы |
| `KbDocuments.jsx` | `src/components/KbDocuments.jsx` | Список документов KB |
| `KbDocumentUpload.jsx` | `src/components/KbDocumentUpload.jsx` | Загрузка нового документа |
| `KbDocumentDetail.jsx` | `src/components/KbDocumentDetail.jsx` | Карточка документа, версии, обработка |
| `AiConfig.jsx` | `src/components/AiConfig.jsx` | Управление версионированной конфигурацией AI: system prompt, retrieval params, prompt parts |
| `Analytics.jsx` | `src/components/Analytics.jsx` | Графики и метрики, включая разбивку latency по компонентам |
| `AuditLog.jsx` | `src/components/AuditLog.jsx` | Журнал аудита |
| `useAuth.js` | `src/hooks/useAuth.js` | Хранение токена |
| `backend.js` | `src/api/backend.js` | HTTP-клиент для admin API |

---

## 5. API клиент

Файл `src/api/backend.js` содержит функции для всех admin endpoints:

- Monitoring: `getMonitoringStatus`
- Knowledge Base: `listKbDocuments`, `uploadKbDocument`, `processKbDocument`, `publishKbDocument`, `uploadKbVersion`, `deleteKbDocument`
- AI Config: `getActiveAiConfig`, `getAiConfigHistory`, `createAiConfig`, `activateAiConfig`
- Analytics: `getAnalyticsDashboard`, `getAnalyticsTopics`, `getAnalyticsUnanswered`, `getAnalyticsFeedback`
- Audit: `getAuditLog`

---

## 6. Дизайн

Admin Console использует тёмную административную тему лаборатории (`ai-portfolio/admin` style):

- фон: `#0b1120`;
- поверхности: `#111827`, `#1e293b`;
- акцент: violet `#7c3aed`;
- текст: `#f8fafc`;
- вторичный текст: `#94a3b8`.

---

## 7. Сборка и развёртывание

```bash
cd admin-console
npm install
npm run build
```

Docker-образ собирается через `docker-compose.yml` как сервис `ai-curator-admin-console`.

```bash
docker compose up -d --build ai-curator-admin-console
```

---

## 8. AI Configuration — детали

Раздел **AI Configuration** позволяет управлять активной версией конфигурации LLM и retrieval.

Редактируемые поля:
- `system_prompt` — роль и правила AI Curator;
- `model`, `temperature`, `max_tokens` — параметры LLM;
- `top_k_retrieval` — сколько чанков KB запрашивать у Chroma;
- `rag_distance_threshold` — порог cosine distance для отсечения нерелевантных чанков;
- `beginner_instructions` / `advanced_instructions` — инструкции по уровню сложности;
- `few_shot_examples` — корректные/некорректные примеры ответов;
- `output_rules` — правила оформления ответа, источников, отказа;
- `refusal_answer_text` — текст отказа на запросы об оценках/дедлайнах;
- `max_history_messages` — количество сообщений истории в промпте.

Каждая новая версия создаётся неактивной; активация производится отдельной кнопкой.

## 9. История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-07-30 | 1.0 | Создан документ |
| 2026-07-30 | 1.1 | Добавлено описание расширенной AI Configuration и latency traces в Analytics |
