# AI Curator — примеры API

Этот каталог содержит примеры запросов и ответов для ключевых endpoints AI Curator.

Полный API-контракт описан в [`../API_CONTRACT.md`](../API_CONTRACT.md).

## Содержание

| Файл | Назначение |
|------|-----------|
| `chat_request.json` | Тело запроса `POST /api/v1/chat` |
| `chat_response.json` | Пример ответа `POST /api/v1/chat` |
| `admin_kb_upload.sh` | curl: загрузка документа в Базе знаний |
| `admin_export_logs.sh` | curl: экспорт operational logs в CSV |
| `demo_session.sh` | curl: получение demo-токена и отправка сообщения |

## Примечания

- Замените `YOUR_ADMIN_TOKEN` и `YOUR_DEMO_TOKEN` на реальные токены.
- Для production-развёртывания используйте HTTPS-URL из `DEPLOYMENT_GUIDE.md`.
- Все примеры используют синтетические данные из единого демо-контекста.
