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
        data = audit_response.json()
        entries = data.get("items", data)
        assert any(
            e["resource_type"] == "kb_document" and str(doc_id) == e["resource_id"]
            for e in entries
        )


@pytest.mark.anyio
async def test_audit_log_date_filters_and_detail(client):
    async with client:
        list_response = await client.get("/api/v1/admin/audit?limit=1")
        assert list_response.status_code == 200
        first_data = list_response.json()
        first_entries = first_data.get("items", first_data)
        assert first_entries
        entry_id = first_entries[0]["id"]

        detail_response = await client.get(f"/api/v1/admin/audit/{entry_id}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["id"] == entry_id
        assert "user_name" in detail
        assert "ip_address" in detail
        assert "details" in detail

        today = __import__("datetime").date.today().isoformat()
        filtered_response = await client.get(
            f"/api/v1/admin/audit?date_from={today}&date_to={today}&limit=100"
        )
        assert filtered_response.status_code == 200
        filtered_data = filtered_response.json()
        filtered = filtered_data.get("items", filtered_data)
        assert any(e["id"] == entry_id for e in filtered)

        far_future = "2099-01-01"
        empty_response = await client.get(
            f"/api/v1/admin/audit?date_from={far_future}&date_to={far_future}"
        )
        assert empty_response.status_code == 200
        empty_data = empty_response.json()
        empty_items = empty_data.get("items", empty_data)
        assert empty_items == []


@pytest.mark.anyio
async def test_audit_log_404_for_missing_entry(client):
    async with client:
        response = await client.get("/api/v1/admin/audit/9999999")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_audit_log_does_not_record_read_only_views(client):
    """Opening /admin/audit, /admin/dialog-sessions and /admin/operational-logs
    must not create new audit entries (no self-generated noise)."""
    async with client:
        before = await client.get("/api/v1/admin/audit?limit=1")
        before_id = before.json()["items"][0]["id"]

        await client.get("/api/v1/admin/audit")
        await client.get("/api/v1/admin/audit/1")
        await client.get("/api/v1/admin/dialog-sessions")
        await client.get("/api/v1/admin/dialog-sessions/nonexistent")
        await client.get("/api/v1/admin/operational-logs")
        await client.get("/api/v1/admin/operational-logs/1")
        await client.get("/api/v1/admin/monitoring/status")
        await client.get("/api/v1/admin/monitoring/errors")
        await client.get("/api/v1/admin/analytics/dashboard")
        await client.get("/api/v1/admin/kb/documents/1/detail")

        after = await client.get("/api/v1/admin/audit?limit=1")
        after_id = after.json()["items"][0]["id"]

        assert before_id == after_id, "Read-only views created audit noise"
