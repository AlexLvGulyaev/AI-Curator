"""Tests for Knowledge Base admin API."""

from pathlib import Path

import pytest


def _make_markdown_file(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "lecture.md"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.unit
@pytest.mark.anyio
async def test_kb_status(client):
    async with client:
        response = await client.get("/api/v1/admin/kb/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["published_documents"], int)


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.integration
@pytest.mark.anyio
async def test_document_detail_bundle(client, tmp_path):
    content = "# Детальная лекция\n\nПример текста для preview.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Detail Bundle Test", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]

        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")

        detail_response = await client.get(f"/api/v1/admin/kb/documents/{doc_id}/detail")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["document"]["id"] == doc_id
        assert detail["active_version"]["version_number"] == 1
        assert detail["active_version"]["sha256"] is not None
        assert detail["active_version"]["cleaned_storage_path"] is not None
        assert detail["execution"]["provider"] == "OpenAI"
        assert detail["execution"]["backend"] == "Chroma"
        assert detail["execution"]["sha256"] == detail["active_version"]["sha256"]
        assert detail["execution"]["postgres_status"] == "indexed"


@pytest.mark.integration
@pytest.mark.anyio
async def test_version_text_and_chunks(client, tmp_path):
    content = "# Claude Code\n\nБыстрый старт с Claude Code.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Version Preview Test", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]
        version_id = create_response.json()["versions"][0]["id"]

        process_response = await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")
        assert process_response.status_code == 200

        text_response = await client.get(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/text"
        )
        assert text_response.status_code == 200
        text_data = text_response.json()
        assert text_data["stage"] == "cleaned"
        assert "Claude Code" in text_data["preview"]

        raw_response = await client.get(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/text?stage=raw"
        )
        assert raw_response.status_code == 200
        raw_data = raw_response.json()
        assert raw_data["stage"] == "raw"
        assert "Claude Code" in raw_data["preview"]

        chunks_response = await client.get(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/chunks"
        )
        assert chunks_response.status_code == 200
        chunks = chunks_response.json()
        assert len(chunks) >= 1
        assert chunks[0]["content_preview"] is not None


@pytest.mark.integration
@pytest.mark.anyio
async def test_document_timeline(client, tmp_path):
    content = "# Timeline test\n\nContent.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Timeline Test", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]

        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")

        timeline_response = await client.get(f"/api/v1/admin/kb/documents/{doc_id}/timeline")
        assert timeline_response.status_code == 200
        timeline = timeline_response.json()
        assert any(event["event_type"] == "upload" for event in timeline)
        index_event = next(
            (e for e in timeline if e["event_type"] == "index_start"), None
        )
        assert index_event is not None
        assert index_event["status"] == "success"
        assert index_event["duration_ms"] is not None
        assert index_event["duration_ms"] >= 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_activate_and_reindex_version(client, tmp_path):
    v1_content = "# Версия 1\n\nКонтент первой версии."
    v2_content = "# Версия 2\n\nКонтент второй версии."

    v1_path = tmp_path / "v1.md"
    v1_path.write_text(v1_content, encoding="utf-8")
    v2_path = tmp_path / "v2.md"
    v2_path.write_text(v2_content, encoding="utf-8")

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Activate Test", "document_type": "lecture"},
            files={"file": ("v1.md", v1_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]
        v1_id = create_response.json()["versions"][0]["id"]

        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")

        add_version_response = await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions",
            files={"file": ("v2.md", v2_path.read_bytes(), "text/markdown")},
        )
        v2_id = add_version_response.json()["versions"][-1]["id"]

        activate_response = await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{v2_id}/activate"
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["active_version_id"] == v2_id

        reindex_response = await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{v1_id}/reindex"
        )
        assert reindex_response.status_code == 200
        assert reindex_response.json()["active_version_id"] == v1_id


@pytest.mark.integration
@pytest.mark.anyio
async def test_reindex_all(client, tmp_path):
    content = "# Reindex all test\n\nContent.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Reindex All Test", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]

        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")
        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/publish?publish=true")

        reindex_all_response = await client.post("/api/v1/admin/kb/reindex-all")
        assert reindex_all_response.status_code == 200
        result = reindex_all_response.json()
        assert result["total"] >= 1
        assert result["processed"] >= 1


@pytest.mark.integration
@pytest.mark.anyio
async def test_save_cleaned_text_and_reindex(client, tmp_path):
    content = "# Original\n\nFirst paragraph.\n\nSecond paragraph.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Cleaned Edit Test", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]
        version_id = create_response.json()["versions"][0]["id"]

        await client.post(f"/api/v1/admin/kb/documents/{doc_id}/process")

        # Fetch original cleaned preview to determine sha256 before edit.
        detail_before = await client.get(f"/api/v1/admin/kb/documents/{doc_id}/detail")
        sha256_before = detail_before.json()["active_version"]["sha256"]

        edited_text = "# Edited\n\nCompletely rewritten content for testing.\n"
        save_response = await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/text",
            params={"stage": "cleaned", "reindex": "true"},
            json={"text": edited_text},
        )
        assert save_response.status_code == 200
        saved = save_response.json()
        assert saved["active_version_id"] == version_id
        assert saved["status"] == "indexed"

        detail_after = await client.get(f"/api/v1/admin/kb/documents/{doc_id}/detail")
        version_after = detail_after.json()["active_version"]
        assert version_after["sha256"] != sha256_before
        assert version_after["cleaned_storage_path"] is not None
        assert detail_after.json()["execution"]["postgres_status"] == "indexed"

        chunks_response = await client.get(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/chunks"
        )
        chunks = chunks_response.json()
        assert len(chunks) >= 1
        assert any("Completely rewritten" in (c["content_preview"] or "") for c in chunks)


@pytest.mark.unit
@pytest.mark.anyio
async def test_save_cleaned_text_without_reindex(client, tmp_path):
    content = "# Original\n\nContent.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Cleaned Edit No Reindex", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]
        version_id = create_response.json()["versions"][0]["id"]

        edited_text = "# Edited without reindex\n\nNew content.\n"
        save_response = await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/text",
            params={"stage": "cleaned", "reindex": "false"},
            json={"text": edited_text},
        )
        assert save_response.status_code == 200
        saved = save_response.json()
        assert saved["status"] == "pending"

        text_response = await client.get(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/text?stage=cleaned"
        )
        assert text_response.status_code == 200
        assert "New content." in text_response.json()["preview"]


@pytest.mark.unit
@pytest.mark.anyio
async def test_save_cleaned_text_rejects_raw_stage(client, tmp_path):
    content = "# Original\n\nContent.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Raw Save Rejected", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]
        version_id = create_response.json()["versions"][0]["id"]

        save_response = await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/text",
            params={"stage": "raw", "reindex": "false"},
            json={"text": "should fail"},
        )
        assert save_response.status_code == 400


@pytest.mark.unit
@pytest.mark.anyio
async def test_save_cleaned_text_rejects_archived_version(client, tmp_path):
    content = "# Original\n\nContent.\n"
    file_path = _make_markdown_file(tmp_path, content)

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Archived Save Rejected", "document_type": "lecture"},
            files={"file": ("lecture.md", file_path.read_bytes(), "text/markdown")},
        )
        doc_id = create_response.json()["id"]
        version_id = create_response.json()["versions"][0]["id"]

        await client.delete(f"/api/v1/admin/kb/documents/{doc_id}")

        save_response = await client.post(
            f"/api/v1/admin/kb/documents/{doc_id}/versions/{version_id}/text",
            params={"stage": "cleaned", "reindex": "false"},
            json={"text": "should fail"},
        )
        assert save_response.status_code == 400
