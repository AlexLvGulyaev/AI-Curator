"""Tests for Business Reports / Quality Reports admin endpoints."""

from datetime import datetime, timezone

import pytest

from models.chat import ChatLog, ChatRequest
from models.knowledge_base import KbDocument, KbDocumentVersion

pytestmark = pytest.mark.unit


@pytest.mark.anyio
async def test_reports_quality_empty(client):
    async with client:
        response = await client.get("/api/v1/admin/reports/quality")
        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 0
        assert data["answered_rate"] == 0
        assert data["error_rate"] == 0


@pytest.mark.anyio
async def test_reports_quality_metrics(client, db_session):
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    # answered RAG
    req_rag = ChatRequest(
        message="explain prompt engineering", intent="study", created_at=base_time
    )
    db_session.add(req_rag)
    log_rag = ChatLog(
        request=req_rag,
        answer="prompt engineering is...",
        sources=[{"type": "kb", "document_id": 1, "chunk_index": 0}],
        feedback_score=8,
        created_at=base_time,
    )
    db_session.add(log_rag)

    # answered cache
    req_cache = ChatRequest(
        message="repeat", intent="study", created_at=base_time
    )
    db_session.add(req_cache)
    log_cache = ChatLog(
        request=req_cache,
        answer="cached",
        cache_hit=True,
        created_at=base_time,
    )
    db_session.add(log_cache)

    # error
    req_err = ChatRequest(
        message="error", intent="study", created_at=base_time
    )
    db_session.add(req_err)
    log_err = ChatLog(
        request=req_err,
        error="LLM timeout",
        created_at=base_time,
    )
    db_session.add(log_err)

    # fallback
    req_fallback = ChatRequest(
        message="out of scope", intent="out_of_scope", created_at=base_time
    )
    db_session.add(req_fallback)
    log_fallback = ChatLog(
        request=req_fallback,
        answer="I cannot help with that",
        created_at=base_time,
    )
    db_session.add(log_fallback)

    # unanswered
    req_unanswered = ChatRequest(
        message="no answer", intent="study", created_at=base_time
    )
    db_session.add(req_unanswered)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/reports/quality")
        assert response.status_code == 200
        data = response.json()

    assert data["total_requests"] == 5
    assert data["answered_count"] == 3
    assert data["answered_rate"] == 60
    assert data["error_count"] == 1
    assert data["error_rate"] == 20
    assert data["fallback_count"] == 1
    assert data["fallback_rate"] == 20
    assert data["cache_hit_count"] == 1
    assert data["cache_hit_rate"] == 20
    assert round(data["average_feedback_score"], 2) == 8
    assert data["rag_eligible_count"] == 2
    assert data["rag_covered_count"] == 1
    assert data["rag_coverage_rate"] == 50


@pytest.mark.anyio
async def test_reports_unanswered(client, db_session):
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    req_answered = ChatRequest(message="answered", intent="study", created_at=base_time)
    db_session.add(req_answered)
    log_answered = ChatLog(request=req_answered, answer="yes", created_at=base_time)
    db_session.add(log_answered)

    req_unanswered = ChatRequest(
        message="no answer", intent="study", course_id=3, created_at=base_time
    )
    db_session.add(req_unanswered)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/reports/unanswered?course_id=3")
        assert response.status_code == 200
        data = response.json()

    assert data["total"] == 1
    assert data["items"][0]["message"] == "no answer"


@pytest.mark.anyio
async def test_reports_kb_gaps(client, db_session):
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    # study without sources -> gap
    req_gap = ChatRequest(
        message="explain recursion", intent="study", created_at=base_time
    )
    db_session.add(req_gap)
    log_gap = ChatLog(
        request=req_gap,
        answer="recursion is...",
        created_at=base_time,
    )
    db_session.add(log_gap)

    # mixed with only LMS source -> gap
    req_mixed_lms = ChatRequest(
        message="deadline and material", intent="mixed",
        lms_calls=[{"url": "http://lms"}], created_at=base_time,
    )
    db_session.add(req_mixed_lms)
    log_mixed_lms = ChatLog(
        request=req_mixed_lms,
        answer="mixed answer",
        sources=[{"type": "lms", "assignment_id": 1}],
        created_at=base_time,
    )
    db_session.add(log_mixed_lms)

    # study with RAG source -> not gap
    req_covered = ChatRequest(
        message="explain loops", intent="study", created_at=base_time
    )
    db_session.add(req_covered)
    log_covered = ChatLog(
        request=req_covered,
        answer="loops are...",
        sources=[{"type": "kb", "document_id": 2, "chunk_index": 0}],
        created_at=base_time,
    )
    db_session.add(log_covered)

    # mixed with error -> not gap
    req_error = ChatRequest(
        message="error question", intent="mixed", created_at=base_time
    )
    db_session.add(req_error)
    log_error = ChatLog(
        request=req_error,
        answer="error",
        error="LLM error",
        created_at=base_time,
    )
    db_session.add(log_error)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/reports/kb-gaps")
        assert response.status_code == 200
        data = response.json()

    assert data["total"] == 2
    messages = {item["message"] for item in data["items"]}
    assert "explain recursion" in messages
    assert "deadline and material" in messages
    assert "explain loops" not in messages
    assert "error question" not in messages


@pytest.mark.anyio
async def test_reports_popular_topics(client, db_session):
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    for _ in range(3):
        req = ChatRequest(message="study msg", intent="study", created_at=base_time)
        db_session.add(req)
    for _ in range(2):
        req = ChatRequest(message="deadline msg", intent="deadline", created_at=base_time)
        db_session.add(req)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/reports/popular-topics")
        assert response.status_code == 200
        data = response.json()

    topics = {item["intent"]: item["count"] for item in data}
    assert topics["study"] == 3
    assert topics["deadline"] == 2


@pytest.mark.anyio
async def test_reports_kb_coverage(client, db_session):
    doc1 = KbDocument(
        title="Lecture 1",
        document_type="lecture",
        course_id=3,
        is_published=True,
    )
    db_session.add(doc1)
    await db_session.flush()
    version1 = KbDocumentVersion(
        document_id=doc1.id,
        version_number=1,
        storage_path="/tmp/1.md",
        original_filename="1.md",
        chunk_count=4,
        is_active=True,
    )
    db_session.add(version1)

    doc2 = KbDocument(
        title="FAQ",
        document_type="faq",
        course_id=None,
        is_published=False,
    )
    db_session.add(doc2)
    await db_session.flush()
    version2 = KbDocumentVersion(
        document_id=doc2.id,
        version_number=1,
        storage_path="/tmp/2.md",
        original_filename="2.md",
        chunk_count=2,
        is_active=True,
    )
    db_session.add(version2)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/reports/kb-coverage")
        assert response.status_code == 200
        data = response.json()

    assert data["total_documents"] == 2
    assert len(data["documents_by_type"]) == 2
    course_row = next(r for r in data["coverage_by_course"] if r["course_id"] == 3)
    assert course_row["total_documents"] == 1
    assert course_row["published_documents"] == 1
    assert course_row["chunk_count"] == 4


@pytest.mark.anyio
async def test_reports_expansion_candidates(client, db_session):
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    for _ in range(3):
        req = ChatRequest(message="study gap", intent="study", created_at=base_time)
        db_session.add(req)
        log = ChatLog(request=req, answer="ans", created_at=base_time)
        db_session.add(log)

    for _ in range(1):
        req = ChatRequest(message="mixed gap", intent="mixed", created_at=base_time)
        db_session.add(req)
        log = ChatLog(request=req, answer="ans", created_at=base_time)
        db_session.add(log)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/reports/expansion-candidates")
        assert response.status_code == 200
        data = response.json()

    assert data[0]["intent"] == "study"
    assert data[0]["gap_count"] == 3
    assert data[1]["intent"] == "mixed"
    assert data[1]["gap_count"] == 1


@pytest.mark.anyio
async def test_reports_export_csv(client, db_session):
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    req_unanswered = ChatRequest(
        message="unanswered question", intent="study", created_at=base_time
    )
    db_session.add(req_unanswered)

    req_gap = ChatRequest(
        message="kb gap question", intent="study", created_at=base_time
    )
    db_session.add(req_gap)
    log_gap = ChatLog(request=req_gap, answer="answer", created_at=base_time)
    db_session.add(log_gap)

    await db_session.commit()

    async with client:
        response = await client.get("/api/v1/admin/reports/export")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        body = response.content.decode("utf-8-sig")
        assert "unanswered" in body
        assert "kb_gap" in body
        assert "unanswered question" in body
        assert "kb gap question" in body
