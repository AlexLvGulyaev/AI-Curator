#!/usr/bin/env python3
"""Upload, process and publish KB content for course 4 (Prompt Engineering).

Generates 15 lecture documents (one per lesson) and 15 instruction documents
(one per assignment) to mirror the structure of course 3 in Knowledge Base.
"""

import os
import sys
import time
from pathlib import Path

import requests

BASE_URL = os.getenv("AI_CURATOR_API_URL", "https://curator-api.alex-n8n.site/api/v1")
TOKEN = os.getenv("ADMIN_CONSOLE_TOKEN")

COURSE_ID = 4

LESSONS = [
    ("PE01. Что такое промпт", [
        "Промпт как запрос к языковой модели.",
        "Зачем нужно умение формулировать промпты.",
        "Отличие промпта от обычного поискового запроса.",
    ]),
    ("PE02. Базовые компоненты запроса", [
        "Инструкция: что именно нужно сделать.",
        "Контекст: фоновая информация.",
        "Входные данные: текст или объект для обработки.",
        "Формат вывода: JSON, Markdown, список, таблица.",
    ]),
    ("PE03. Чего избегать при написании промптов", [
        "Двусмысленные формулировки.",
        "Избыточный или недостаточный контекст.",
        "Запросы, требующие приватных данных.",
    ]),
    ("PE04. Ролевые промпты", [
        "Как роль влияет на стиль ответа.",
        "Примеры ролей: учитель, разработчик, аналитик.",
        "Когда ролевой промпт особенно полезен.",
    ]),
    ("PE05. Контекстные промпты", [
        "Подача нужного фона для задачи.",
        "Баланс между полнотой и краткостью контекста.",
        "Примеры хорошего и плохого контекста.",
    ]),
    ("PE06. Комбинация роли и контекста", [
        "Роль + контекст + задача = точный ответ.",
        "Шаблон для сложных запросов.",
        "Практический пример переписи текста.",
    ]),
    ("PE07. Chain-of-thought", [
        "Пошаговое рассуждение модели.",
        "Zero-shot CoT: фраза 'разберём пошагово'.",
        "Когда CoT повышает точность.",
    ]),
    ("PE08. Zero-shot и few-shot", [
        "Zero-shot: запрос без примеров.",
        "Few-shot: 2–3 примера входа и выхода.",
        "Выбор подхода под задачу.",
    ]),
    ("PE09. Структурирование сложных запросов", [
        "Разбиение сложной задачи на этапы.",
        "Явное указание порядка действий.",
        "Пример: анализ, классификация, рекомендации.",
    ]),
    ("PE10. Итеративная разработка", [
        "Цикл: написать промпт → получить ответ → найти слабое место → улучшить.",
        "Что именно улучшать: инструкцию, контекст, формат.",
        "Ведение библиотеки проверенных промптов.",
    ]),
    ("PE11. Обработка ошибок", [
        "Просьба к модели вернуть структурированный отказ.",
        "Работа с неполными или противоречивыми данными.",
        "Пример: 'если данных недостаточно, верни JSON с полем error'.",
    ]),
    ("PE12. Этика и безопасность", [
        "Не запрашивать персональные данные.",
        "Проверка фактов в чувствительных областях.",
        "Прозрачность: сообщать, что ответ создан AI.",
    ]),
    ("PE13. Промпты в бизнесе", [
        "Классификация обращений клиентов.",
        "Генерация маркетинговых текстов.",
        "Автоматизация отчётов и резюме.",
    ]),
    ("PE14. Промпты в образовании", [
        "Объяснение сложных тем простым языком.",
        "Генерация тестов и заданий.",
        "Обратная связь по работам студентов.",
    ]),
    ("PE15. Итоговый проект", [
        "Выбор реальной задачи для автоматизации промптами.",
        "Итеративная доводка 5 промптов.",
        "Оформление портфолио из проверенных решений.",
    ]),
]


def build_lecture_markdown(title: str, bullets: list) -> str:
    return f"# {title}\n\n## Цель урока\n\nПосле прохождения этого урока вы сможете применять концепции темы '{title}' на практике.\n\n## Основные моменты\n\n" + "\n".join(f"- {b}" for b in bullets) + "\n\n## Практическое применение\n\nИспользуйте изученные приёмы при составлении следующих промптов для курса.\n"


def build_assignment_markdown(title: str) -> str:
    return f"# {title}\n\n## Описание задания\n\nВыполните практическое задание по теме урока. Результат пришлите в формате, указанном преподавателем.\n\n## Критерии проверки\n\n- Понимание темы.\n- Корректность примеров.\n- Соблюдение формата вывода.\n\n## Рекомендации\n\nИспользуйте шаблон RICE (Role, Instruction, Context, Expectation) при составлении промптов.\n"


def upload_file(file_path: Path, title: str, doc_type: str) -> int:
    url = f"{BASE_URL}/admin/kb/documents"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = {
        "title": title,
        "document_type": doc_type,
        "course_id": str(COURSE_ID),
        "difficulty": "beginner",
        "language": "ru",
    }
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f, "text/markdown")}
        resp = requests.post(url, headers=headers, data=data, files=files, timeout=120)
    resp.raise_for_status()
    return resp.json()["id"]


def process_document(doc_id: int) -> None:
    url = f"{BASE_URL}/admin/kb/documents/{doc_id}/process"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    resp = requests.post(url, headers=headers, timeout=300)
    resp.raise_for_status()


def publish_document(doc_id: int) -> None:
    url = f"{BASE_URL}/admin/kb/documents/{doc_id}/publish"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    resp = requests.post(url, headers=headers, params={"publish": "true"}, timeout=60)
    resp.raise_for_status()


def main() -> int:
    if not TOKEN:
        print("ADMIN_CONSOLE_TOKEN is not set", file=sys.stderr)
        return 1

    tmp_dir = Path("/tmp/kb_course4_v2")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    doc_ids = []
    for idx, (lesson_title, bullets) in enumerate(LESSONS, start=1):
        lecture_path = tmp_dir / f"lecture_{idx:02d}.md"
        lecture_path.write_text(build_lecture_markdown(lesson_title, bullets), encoding="utf-8")
        print(f"Uploading lecture {idx}: {lesson_title}")
        doc_id = upload_file(lecture_path, lesson_title, "lecture")
        print(f"  -> document id {doc_id}")
        doc_ids.append(doc_id)

        assign_title = f"ДЗ: {lesson_title}"
        assign_path = tmp_dir / f"assignment_{idx:02d}.md"
        assign_path.write_text(build_assignment_markdown(assign_title), encoding="utf-8")
        print(f"Uploading assignment {idx}: {assign_title}")
        doc_id = upload_file(assign_path, assign_title, "instruction")
        print(f"  -> document id {doc_id}")
        doc_ids.append(doc_id)

    for doc_id in doc_ids:
        print(f"Processing document {doc_id}...")
        process_document(doc_id)
        print("  -> processed")
        time.sleep(1)

    for doc_id in doc_ids:
        print(f"Publishing document {doc_id}...")
        publish_document(doc_id)
        print("  -> published")

    print("Done. Document IDs:", doc_ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
