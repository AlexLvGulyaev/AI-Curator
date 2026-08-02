"""Tests for RAG pipeline and search endpoints."""

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_rag_process_and_search(client, tmp_path):
    content = (
        "# Claude Code: быстрый старт\n\n"
        "Claude Code — это инструмент командной строки от Anthropic, "
        "который позволяет взаимодействовать с Claude прямо в терминале. "
        "Он помогает писать код, искать ошибки и автоматизировать рутинные задачи.\n\n"
        "## Установка\n\n"
        "Для установки Claude Code выполните команду npm install -g @anthropic-ai/claude-code. "
        "После установки запустите claude и авторизуйтесь через браузер.\n\n"
        "## Первый запуск\n\n"
        "Первый запуск Claude Code требует выбора рабочей директории и подтверждения доступа к файлам."
    )
    file_path = tmp_path / "claude-code-intro.md"
    file_path.write_text(content, encoding="utf-8")

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={
                "title": "Claude Code Intro",
                "document_type": "lecture",
                "course_id": 3,
                "module_id": 1,
                "difficulty": "beginner",
                "language": "ru",
            },
            files={"file": ("claude-code-intro.md", file_path.read_bytes(), "text/markdown")},
        )
        assert create_response.status_code == 201
        doc = create_response.json()
        doc_id = doc["id"]
        assert doc["status"] == "pending"

        process_response = await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")
        assert process_response.status_code == 200
        processed = process_response.json()
        assert processed["status"] == "indexed"
        assert processed["versions"][0]["status"] == "indexed"
        assert processed["versions"][0]["chunk_count"] >= 1

        search_response = await client.post(
            "/api/v1/rag/search",
            json={"query": "установка Claude Code npm", "course_id": 3, "k": 3},
        )
        assert search_response.status_code == 200
        search_data = search_response.json()
        assert search_data["query"] == "установка Claude Code npm"
        assert search_data["total"] >= 1
        contents = " ".join(r["content"] for r in search_data["results"])
        assert "npm" in contents or "установка" in contents


@pytest.mark.anyio
async def test_rag_version_replacement(client, tmp_path):
    v1_content = "# Версия 1\n\nКлючевая информация: alpha-концепт Claude Code."
    v2_content = "# Версия 2\n\nКлючевая информация: beta-функционал Claude Code."

    v1_path = tmp_path / "v1.md"
    v1_path.write_text(v1_content, encoding="utf-8")
    v2_path = tmp_path / "v2.md"
    v2_path.write_text(v2_content, encoding="utf-8")

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Version Replacement Test", "document_type": "lecture"},
            files={"file": ("v1.md", v1_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]

        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")
        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/publish?publish=true")

        await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions",
            files={"file": ("v2.md", v2_path.read_bytes(), "text/markdown")},
        )
        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/publish?publish=true")
        process_response = await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")
        processed = process_response.json()
        active_version_id = processed["active_version_id"]
        assert active_version_id is not None

        search_response = await client.post(
            "/api/v1/rag/search",
            json={"query": "Claude Code beta", "document_id": doc_id, "k": 5},
        )
        assert search_response.status_code == 200
        results = search_response.json()["results"]
        assert len(results) >= 1
        # Every returned chunk must belong to the latest active version.
        for result in results:
            assert result["metadata"]["version_id"] == active_version_id
