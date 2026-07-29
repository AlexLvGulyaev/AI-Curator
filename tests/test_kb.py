"""Tests for Knowledge Base admin API."""

from pathlib import Path

import pytest


def _make_markdown_file(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "lecture.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.anyio
async def test_kb_status(client):
    async with client:
        response = await client.get("/api/v1/admin/kb/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["published_documents"], int)


@pytest.mark.anyio
async def test_create_and_get_document(client, tmp_path):
    content = "# Заголовок\n\nТекст лекции по Claude Code.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={
                "title": "Test Lecture",
                "document_type": "lecture",
                "course_id": 3,
                "module_id": 1,
                "difficulty": "beginner",
                "language": "ru",
                "description": "Test description",
            },
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert created["title"] == "Test Lecture"
        assert created["status"] == "pending"
        assert created["is_published"] is False
        assert len(created["versions"]) == 1

        get_response = await client.get(f"/api/v1/admin/kb/documents/{created['id']}")
        assert get_response.status_code == 200
        fetched = get_response.json()
        assert fetched["id"] == created["id"]


@pytest.mark.anyio
async def test_unsupported_file_type(client, tmp_path):
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03")

    async with client:
        response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Bad file", "document_type": "lecture"},
            files={"file": ("data.bin", file_path.read_bytes(), "application/octet-stream")},
        )
        assert response.status_code == 415


@pytest.mark.anyio
async def test_publish_document(client, tmp_path):
    content = "# Лекция\n\nТекст.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Publish Test", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]

        response = await client.post(f"/api/v1/admin/kb/documents/{doc_id}/publish?publish=true")
        assert response.status_code == 200
        assert response.json()["is_published"] is True
