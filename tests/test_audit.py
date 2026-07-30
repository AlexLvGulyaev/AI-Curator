"""Tests for audit log admin endpoints."""

import pytest


@pytest.mark.anyio
async def test_audit_log_after_kb_create(client, tmp_path):
    file_path = tmp_path / "audit.md"
    file_path.write_text("# Audit test\n", encoding="utf-8")

    async with client:
        create_response = await client.post(
            "/api/v1/admin/kb/documents",
            data={"title": "Audit Doc", "document_type": "lecture"},
            files={"file": ("audit.md", file_path.read_bytes(), "text/markdown")},
        )
        assert create_response.status_code == 201
        doc_id = create_response.json()["id"]

        audit_response = await client.get("/api/v1/admin/audit")
        assert audit_response.status_code == 200
        entries = audit_response.json()
        assert any(
            e["resource_type"] == "kb_document" and str(doc_id) == e["resource_id"]
            for e in entries
        )
