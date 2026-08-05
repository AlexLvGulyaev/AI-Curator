# 🖥️ ADMIN_CONSOLE.md — AI Curator Admin Console

**Проект:** ai-curator  
**Версия:** 1.1  
**Дата:** 2026-08-05  
**Статус:** Актуален — компонент Admin Console AI Curator

🌐 **Консоль администратора:** [▶️ Открыть админ-панель](https://curator-admin.alex-n8n.site)

---

## 🎯 1. Назначение

Admin Console AI Curator — отдельный публичный веб-интерфейс для администраторов и методистов. Позволяет управлять Knowledge Base, конфигурацией AI, просматривать аналитику, операционные логи, диалоговые сессии и журнал аудита.

---

## 🛠️ 2. Стек

- React 18
- Vite 5
- Tailwind CSS 3
- Recharts (графики аналитики)
- react-markdown + rehype-sanitize (рендеринг markdown)
- nginx (статический хостинг)
- Docker + Docker Compose

---

## 🔐 3. Аутентификация

Admin Console использует статический Bearer-токен из переменной окружения `ADMIN_CONSOLE_TOKEN`.

При входе токен сохраняется в `localStorage` и передаётся в заголовке `Authorization: Bearer <token>` для всех запросов к `/api/v1/admin/*`.

Если `ADMIN_CONSOLE_TOKEN` не задан или равен плейсхолдеру, административные endpoints не требуют авторизации (не рекомендуется для production).

---

## 🧩 4. Структура компонентов

| Компонент | Размещение | Назначение |
|-----------|------------|------------|
| `Login.jsx` | `src/components/Login.jsx` | Ввод Bearer-токена |
| `Sidebar.jsx` | `src/components/Sidebar.jsx` | Навигация по разделам |
| `Dashboard.jsx` | `src/components/Dashboard.jsx` | Панель состояния системы и KPI |
| `KbDocuments.jsx` | `src/components/KbDocuments.jsx` | Трёхпанельная консоль Базы знаний |
| `KbDocumentList.jsx` | `src/components/KbDocumentList.jsx` | Список документов KB |
| `KbDocumentUpload.jsx` | `src/components/KbDocumentUpload.jsx` | Форма загрузки нового документа |
| `KbDocumentSummary.jsx` | `src/components/KbDocumentSummary.jsx` | Сводка документа: паспорт, версии, чанки |
| `KbDocumentLifecycle.jsx` | `src/components/KbDocumentLifecycle.jsx` | Timeline жизненного цикла документа |
| `KbDocumentTextEditor.jsx` | `src/components/KbDocumentTextEditor.jsx` | Редактор текста документа |
| `KbDocumentToolbar.jsx` | `src/components/KbDocumentToolbar.jsx` | Панель действий документа |
| `AiConfig.jsx` | `src/components/AiConfig.jsx` | Управление версионированной конфигурацией AI |
| `AiAndRetrievalConfig.jsx` | `src/components/AiAndRetrievalConfig.jsx` | AI и retrieval параметры |
| `OrchestratorConfig.jsx` | `src/components/OrchestratorConfig.jsx` | Настройки оркестратора: интенты, routing, fallback |
| `Analytics.jsx` | `src/components/Analytics.jsx` | Графики и метрики использования |
| `Reports.jsx` | `src/components/Reports.jsx` | Управленческие отчёты и качество ответов |
| `OperationalLogs.jsx` | `src/components/OperationalLogs.jsx` | Операционные логи с фильтрами и CSV export |
| `DialogSessions.jsx` | `src/components/DialogSessions.jsx` | Диалоговые сессии и timeline обработки |
| `AuditLog.jsx` | `src/components/AuditLog.jsx` | Журнал аудита административных событий |
| `OperationalModalityBadge.jsx` | `src/components/OperationalModalityBadge.jsx` | Бейджи режимов LMS/RAG/mixed |
| `OperationalPipelineStageIcon.jsx` | `src/components/OperationalPipelineStageIcon.jsx` | Иконки этапов pipeline |
| `SessionJsonSnapshot.jsx` | `src/components/SessionJsonSnapshot.jsx` | JSON-снимок диалоговой сессии |
| `useAuth.js` | `src/hooks/useAuth.js` | Хранение и проверка токена |
| `backend.js` | `src/api/backend.js` | HTTP-клиент для admin API |

---

## 🔌 5. API клиент

Файл `src/api/backend.js` содержит функции для всех admin endpoints:

- Monitoring: `getMonitoringStatus`
- Knowledge Base: `listKbDocuments`, `uploadKbDocument`, `processKbDocument`, `uploadKbVersion`
- AI Config: `getActiveAiConfig`, `getAiConfigHistory`, `createAiConfig`, `activateAiConfig`
- Orchestrator: `getOrchestratorConfig`, `updateOrchestratorConfig`
- Analytics: `getAnalyticsDashboard`, `getAnalyticsTopics`, `getAnalyticsUnanswered`, `getAnalyticsFeedback`
- Reports: `getReportsDashboard`
- Operational Logs: `getOperationalLogs`, `exportOperationalLogsCsv`
- Dialog Sessions: `getDialogSessions`, `getDialogSessionDetail`
- Audit: `getAuditLog`, `exportAuditLogCsv`

---

## 🎨 6. Дизайн

Admin Console использует тёмную административную тему лаборатории (`ai-portfolio/admin` style):

| Роль | Цвет | Пример |
|------|------|--------|
| Фон | `#0b1120` | ████ `#0b1120` |
| Поверхности | `#111827`, `#1e293b` | ████ `#111827` · ████ `#1e293b` |
| Акцент | violet `#7c3aed` | ████ `#7c3aed` |
| Текст | `#f8fafc` | ████ `#f8fafc` |
| Вторичный текст | `#94a3b8` | ████ `#94a3b8` |

---

## 📦 7. Сборка и развёртывание

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

## ⚙️ 8. AI Configuration — детали

Раздел **AI Configuration** позволяет управлять активной версией конфигурации LLM и retrieval.

Редактируемые поля:
- `system_prompt` — роль и правила AI Curator;
- `model`, `temperature`, `max_tokens` — параметры LLM;
- `active_provider` — активный LLM-провайдер (`openai`, `gigachat`);
- `fallback_provider` — резервный провайдер при недоступности основного;
- `top_k_retrieval` — сколько чанков KB запрашивать у Chroma;
- `rag_distance_threshold` — порог cosine distance для отсечения нерелевантных чанков;
- `beginner_instructions` / `advanced_instructions` — инструкции по уровню сложности;
- `few_shot_examples` — корректные/некорректные примеры ответов;
- `output_rules` — правила оформления ответа, источников, отказа;
- `refusal_answer_text` — текст отказа на запросы об оценках/дедлайнах;
- `max_history_messages` — количество сообщений истории в промпте.

Каждая новая версия создаётся неактивной; активация производится отдельной кнопкой.

## 📝 9. История изменений

| Дата | Версия | Изменения |
|------|--------|-----------|
| 2026-07-30 | 1.0 | Создан документ |
| 2026-08-05 | 1.1 | Актуализировано под текущий состав панелей (Analytics, Reports, Logs, Dialog Sessions, Audit, export) |
