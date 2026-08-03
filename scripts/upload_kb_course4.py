#!/usr/bin/env python3
"""Upload, process and publish KB lectures for course 4 (Prompt Engineering)."""

import os
import sys
import time
from pathlib import Path

import requests

BASE_URL = os.getenv("AI_CURATOR_API_URL", "https://curator-api.alex-n8n.site/api/v1")
TOKEN = os.getenv("ADMIN_CONSOLE_TOKEN")

MODULES = [
    ("module1_basics.md", "Модуль 1. Основы промпт-инжиниринга", "lecture"),
    ("module2_structure.md", "Модуль 2. Структура эффективного промпта", "lecture"),
    ("module3_role_context.md", "Модуль 3. Ролевые и контекстные промпты", "lecture"),
    ("module4_chain_of_thought.md", "Модуль 4. Chain-of-thought и структурирование", "lecture"),
    ("module5_practice.md", "Модуль 5. Практические применения", "lecture"),
]


def upload_file(file_path: Path, title: str, doc_type: str) -> int:
    url = f"{BASE_URL}/admin/kb/documents"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    data = {
        "title": title,
        "document_type": doc_type,
        "course_id": "4",
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

    base_dir = Path(__file__).resolve().parent.parent / "kb_course4"
    if not base_dir.exists():
        print(f"Directory not found: {base_dir}", file=sys.stderr)
        return 1

    doc_ids = []
    for filename, title, doc_type in MODULES:
        file_path = base_dir / filename
        if not file_path.exists():
            print(f"File not found: {file_path}", file=sys.stderr)
            return 1
        print(f"Uploading {filename}...")
        doc_id = upload_file(file_path, title, doc_type)
        print(f"  -> document id {doc_id}")
        doc_ids.append(doc_id)

    for doc_id in doc_ids:
        print(f"Processing document {doc_id}...")
        process_document(doc_id)
        print(f"  -> processed")
        # Small delay to avoid overloading embedding service.
        time.sleep(1)

    for doc_id in doc_ids:
        print(f"Publishing document {doc_id}...")
        publish_document(doc_id)
        print(f"  -> published")

    print("Done. Document IDs:", doc_ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
