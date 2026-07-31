#!/usr/bin/env python3
"""Upload lecture and assignment markdown files from kb-content into KB.

Uses the internal KnowledgeBaseService directly, bypassing admin auth.
"""

import asyncio
import sys
from pathlib import Path

# Allow running both locally and inside the Docker container.
_script_dir = Path(__file__).resolve().parent
_repo_root = _script_dir.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))
_possible_src = _repo_root / "src"
if _possible_src.exists() and str(_possible_src) not in sys.path:
    sys.path.insert(0, str(_possible_src))

from db import AsyncSessionLocal
from models.knowledge_base import DocumentStatus
from schemas.knowledge_base import KbDocumentCreate
from services.knowledge_base import KnowledgeBaseService
from services.kb_git import KbGitService
from config import settings

KB_CONTENT_ROOT = _repo_root / "kb-content"
KB_COURSE_DIR = KB_CONTENT_ROOT / "courses" / "3"


# Map file stems to module and topic id based on course structure.
# Module 1: lessons CC01-CC03, Module 2: CC05-CC07, Module 3: CC09-CC11.
LESSON_MODULE_MAP = {
    "cc01-installation-first-run": (1, 9),
    "cc02-interface-commands": (1, 10),
    "cc03-first-dialog": (1, 11),
    "cc05-prompt-structure": (2, 13),
    "cc06-role-prompts-context": (2, 14),
    "cc07-chain-of-thought": (2, 15),
    "cc09-automation-routine": (3, 17),
    "cc10-workflow-integration": (3, 18),
    "cc11-final-project": (3, 19),
}

ASSIGNMENT_MODULE_MAP = {
    "hw01-installation-first-run": (1, 24),
    "hw02-interface-commands": (1, 25),
    "hw03-first-dialog": (1, 26),
    "hw05-prompt-structure": (2, 27),
    "hw06-role-prompts-context": (2, 28),
    "hw07-chain-of-thought": (2, 29),
    "hw09-automation-routine": (3, 30),
    "hw10-workflow-integration": (3, 31),
    "hw11-final-project": (3, 32),
}


def _build_create_data(title: str, module_id: int, topic_id: int, doc_type: str) -> KbDocumentCreate:
    return KbDocumentCreate(
        title=title,
        document_type=doc_type,
        course_id=3,
        module_id=module_id,
        topic_id=topic_id,
        difficulty="beginner",
        language="ru",
        description=None,
        source_url=None,
    )


async def _upload_file(service: KnowledgeBaseService, file_path: Path, data: KbDocumentCreate):
    from fastapi import UploadFile

    content = file_path.read_bytes()
    # Minimal UploadFile-like wrapper for the service helper.
    class _FakeUploadFile:
        def __init__(self, filename: str, content: bytes, content_type: str):
            self.filename = filename
            self.content_type = content_type
            self.file = __import__("io").BytesIO(content)

    upload = _FakeUploadFile(file_path.name, content, "text/markdown")
    document = await service.create_document(data, upload)
    return document


async def main():
    async with AsyncSessionLocal() as db:
        service = KnowledgeBaseService(db)

        # Upload lectures
        lectures_dir = KB_COURSE_DIR / "lectures"
        for stem, (module_id, topic_id) in LESSON_MODULE_MAP.items():
            file_path = lectures_dir / f"{stem}.md"
            if not file_path.exists():
                print(f"SKIP: {file_path} not found")
                continue

            title_map = {
                "cc01-installation-first-run": "CC01. Установка и первый запуск Claude Code",
                "cc02-interface-commands": "CC02. Интерфейс и основные команды Claude Code",
                "cc03-first-dialog": "CC03. Первый диалог с Claude Code",
                "cc05-prompt-structure": "CC05. Структура эффективного промпта",
                "cc06-role-prompts-context": "CC06. Ролевые промпты и контекст",
                "cc07-chain-of-thought": "CC07. Chain-of-thought и разбор сложных задач",
                "cc09-automation-routine": "CC09. Claude Code и автоматизация рутины",
                "cc10-workflow-integration": "CC10. Интеграция Claude Code в рабочий процесс",
                "cc11-final-project": "CC11. Итоговый проект: автоматизация с Claude Code",
            }
            title = title_map.get(stem, stem)
            data = _build_create_data(title, module_id, topic_id, "lecture")

            document = await _upload_file(service, file_path, data)
            print(f"UPLOAD lecture: id={document.id} title={document.title}")

            # Process and publish
            await service.process_document(document.id)
            await service.toggle_publish(document.id, True)
            print(f"  published doc {document.id}")

        # Upload assignments
        assignments_dir = KB_COURSE_DIR / "assignments"
        for stem, (module_id, topic_id) in ASSIGNMENT_MODULE_MAP.items():
            file_path = assignments_dir / f"{stem}.md"
            if not file_path.exists():
                print(f"SKIP: {file_path} not found")
                continue

            title_map = {
                "hw01-installation-first-run": "ДЗ: Установка и первый запуск Claude Code",
                "hw02-interface-commands": "ДЗ: Интерфейс и основные команды",
                "hw03-first-dialog": "ДЗ: Первый диалог с Claude Code",
                "hw05-prompt-structure": "ДЗ: Структура эффективного промпта",
                "hw06-role-prompts-context": "ДЗ: Ролевые промпты и контекст",
                "hw07-chain-of-thought": "ДЗ: Chain-of-thought и разбор сложных задач",
                "hw09-automation-routine": "ДЗ: Claude Code и автоматизация рутины",
                "hw10-workflow-integration": "ДЗ: Интеграция Claude Code в рабочий процесс",
                "hw11-final-project": "ДЗ: Итоговый проект",
            }
            title = title_map.get(stem, stem)
            data = _build_create_data(title, module_id, topic_id, "instruction")

            document = await _upload_file(service, file_path, data)
            print(f"UPLOAD assignment: id={document.id} title={document.title}")

            await service.process_document(document.id)
            await service.toggle_publish(document.id, True)
            print(f"  published doc {document.id}")


if __name__ == "__main__":
    asyncio.run(main())
