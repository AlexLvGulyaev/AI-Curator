"""Tests for analytics admin endpoints."""

from datetime import datetime, timezone

import pytest

from models.chat import ChatLog, ChatRequest

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_analytics_dashboard_empty(client):
    async with client:
        response = await client.get("/api/v1/admin/analytics/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 0
        assert data["unanswered_count"] == 0


@pytest.mark.anyio
async def test_analytics_sources_breakdown(client, db_session):
    """Source breakdown should classify lms, rag, both, cache, fallback and error."""
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    # LMS only
    req_lms = ChatRequest(message="lms request", lms_calls=[{"url": "http://lms"}], created_at=base_time)
    db_session.add(req_lms)
    log_lms = ChatLog(request=req_lms, answer="lms answer", created_at=base_time)
    db_session.add(log_lms)

    # RAG/KB only
    req_rag = ChatRequest(message="rag request", created_at=base_time)
    db_session.add(req_rag)
    log_rag = ChatLog(
        request=req_rag,
        answer="rag answer",
        sources=[{"type": "kb", "document_id": 1, "chunk_index": 0}],
        created_at=base_time,
    )
    db_session.add(log_rag)

    # Both LMS and RAG
    req_both = ChatRequest(message="both request", lms_calls=[{"url": "http://lms"}], created_at=base_time)
    db_session.add(req_both)
    log_both = ChatLog(
        request=req_both,
        answer="both answer",
        sources=[{"type": "kb", "document_id": 2, "chunk_index": 0}],
        created_at=base_time,
    )
    db_session.add(log_both)

    # Cache hit
    req_cache = ChatRequest(message="cache request", created_at=base_time)
    db_session.add(req_cache)
    log_cache = ChatLog(request=req_cache, answer="cache answer", cache_hit=True, created_at=base_time)
    db_session.add(log_cache)

    # Backend fallback (out_of_scope without sources and without error)
    req_fallback = ChatRequest(message="fallback request", intent="out_of_scope", created_at=base_time)
    db_session.add(req_fallback)
    log_fallback = ChatLog(request=req_fallback, answer="fallback answer", created_at=base_time)
    db_session.add(log_fallback)

    # Technical error (no sources, but ChatLog.error set)
    req_error = ChatRequest(message="error request", created_at=base_time)
    db_session.add(req_error)
    log_error = ChatLog(request=req_error, error="LLM timeout", created_at=base_time)
    db_session.add(log_error)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/analytics/sources")
        assert response.status_code == 200
        data = response.json()

    breakdown = {item["source"]: item["count"] for item in data["breakdown"]}
    assert breakdown["lms"] == 1
    assert breakdown["rag"] == 1
    assert breakdown["both"] == 1
    assert breakdown["cache"] == 1
    assert breakdown["fallback"] == 1
    assert breakdown["error"] == 1
    assert data["total"] == 6
