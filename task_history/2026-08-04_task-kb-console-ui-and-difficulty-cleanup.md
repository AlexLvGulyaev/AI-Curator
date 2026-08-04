# Task: Консоль «База знаний» — убрать difficulty, поправить UI

**Статус:** ✅ Completed

---

## Исходное задание

1. Переименовать пункт главного меню **Knowledge Base → База знаний**.
2. Убедиться, что сервисы загрузки документов работают.
3. Разобраться с семантикой поля **difficulty** в карточке KB-документа.
4. Убрать поле **difficulty** из карточки KB-документа (frontend), игнорировать его в backend, не менять структуру БД.
5. Сделать нормальную ширину поля **Описание** в модальном окне редактирования/загрузки документа.
6. Исправить отображение строки **«Курс / Модуль / Тема»** в сводке документа (сдвинуть значения вправо, чтобы метка была полностью видна).

---

## Контекст

В карточке KB-документа было поле **difficulty** с тремя значениями (`beginner`/`intermediate`/`advanced`). Оно сохранялось в метаданные чанков Chroma, но в chat-пайплайне не использовалось как фильтр retrieval. В чате difficulty уже управляется через `beginner_instructions` / `advanced_instructions` в AI Config. Получалось, что один термин имел два SOT — решено оставить единый SOT в чате, а в KB difficulty больше не выводить и не использовать.

---

## Что сделано

### 1. Переименование меню
- `admin-console/src/components/Sidebar.jsx`: пункт меню `Knowledge Base` → `База знаний`.

### 2. Убрано поле difficulty из карточки KB
- `admin-console/src/components/KbDocumentUpload.jsx` — убран `DIFFICULTIES`, select, form-поле, `formData.append('difficulty', ...)`.
- `admin-console/src/components/KbDocumentEditModal.jsx` — убран `DIFFICULTIES`, select, загрузка/сохранение `difficulty`.
- `admin-console/src/components/KbDocumentSummary.jsx` — убрана строка «Сложность».

### 3. Backend — игнорируем difficulty, БД не трогаем
- `src/api/v1/admin/kb.py` — `difficulty: str = Form(None)` для обратной совместимости.
- `src/services/knowledge_base.py`:
  - при создании документа `difficulty` всегда `DifficultyLevel.BEGINNER` (колонка `NOT NULL`);
  - при обновлении `difficulty` удаляется из `update_data` (`pop`) и не применяется;
  - в `index_chunks` больше не передаётся `difficulty`.
- `src/services/rag_pipeline.py` — `_build_metadata` больше не пишет `difficulty` в Chroma-метаданные, если она не передана.
- `src/services/prompt_builder.py` — убран вывод `difficulty` в RAG-контексте.

### 4. Исправлено поле «Описание»
- В `KbDocumentEditModal` и `KbDocumentUpload`:
  - `rows={8}`, `min-height: 200px`, `resize: vertical`;
  - поле на всю ширину (`sm:col-span-2`).
- В `admin-console/src/index.css` добавлен селектор `.ai-modal form .ai-textarea`, который переопределяет глобальное `.ai-modal .ai-textarea` (используется текстовым редактором документа) и убирает неправильные `margin`/`width: auto`/`flex: 1` для textarea внутри форм.

### 5. Исправлено отображение «Курс / Модуль / Тема»
- `KbDocumentSummary.jsx`:
  - ширина колонки меток увеличена с `5.5rem` до `7.5rem`;
  - убран `truncate` у самой метки, значения сдвинуты вправо и по-прежнему `truncate` с `title`.

### 6. Тесты и документация
- `tests/test_kb.py`, `tests/test_rag.py` — убран параметр `difficulty` из запросов.
- `docs/API_CONTRACT.md` — убраны `difficulty` из таблиц и примера KB-ответа.
- `docs/PROMPT_ARCHITECTURE.md` — убран `difficulty` из шаблона RAG-фрагмента.

---

## Проверки

- `npm run build` в `admin-console/` — ✅.
- `pytest tests/` в backend-контейнере — **78 passed, 1 warning**.
- `docker compose up -d --build ai-curator-backend ai-curator-admin-console` — ✅.
- `https://curator-admin.alex-n8n.site` — 200 OK.
- `https://curator-api.alex-n8n.site/api/v1/health` — 200 OK.
- Визуально проверено:
  - поле «Описание» в модальном окне — широкое, высокое, ресайзится по вертикали;
  - строка «Курс / Модуль / Тема» в сводке — полностью видна;
  - поля «Сложность» больше нет в карточке и загрузке.

---

## Файлы изменений

1. `admin-console/src/components/Sidebar.jsx`
2. `admin-console/src/components/KbDocumentUpload.jsx`
3. `admin-console/src/components/KbDocumentEditModal.jsx`
4. `admin-console/src/components/KbDocumentSummary.jsx`
5. `admin-console/src/index.css`
6. `src/api/v1/admin/kb.py`
7. `src/services/knowledge_base.py`
8. `src/services/rag_pipeline.py`
9. `src/services/prompt_builder.py`
10. `tests/test_kb.py`
11. `tests/test_rag.py`
12. `docs/API_CONTRACT.md`
13. `docs/PROMPT_ARCHITECTURE.md`

---

## Git

- Коммиты:
  - `88bf778` — fix(ai-curator): remove difficulty from KB UI and stop using it in retrieval/metadata; widen description field
  - `78081b1` — fix(ai-curator): widen KB description and fix summary label alignment
  - `18672cd` — fix(ai-curator): override modal textarea CSS for KB metadata forms
- Ветка: `main`
- Репозиторий: `https://github.com/AlexLvGulyaev/AI-Curator.git`

---

## Handoff — что осталось для следующей сессии

Консоль «База знаний» по этой задаче завершена. Следующая сессия должна продолжить E2E-прогон Admin Console:

1. **Operational Logs** — пройти вручную, найти UI/UX дефекты.
2. **Dialog Sessions** — пройти вручную, найти дефекты.
3. **Журнал аудита** — пройти вручную, найти дефекты.
4. **Web UI** — отдельный UI-дефект: некрасивый рендеринг LMS-источников (эмодзи 🎓 + повтор названия, без URL).
5. **Архитектурный техдолг** — сделать `priority` в Orchestrator полностью честным для всех интентов (если приоритетно).

Также остаётся доработка E2E-чек-листов для оставшихся экранов Admin Console.

---

## Статус

- ✅ Все пункты задачи по консоли «База знаний» выполнены.
- ✅ Код задеплоен на продакшен.
- ✅ Тесты проходят.
- ✅ Git: изменения закоммичены и запушены в `main`.
