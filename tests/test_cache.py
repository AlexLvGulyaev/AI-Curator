"""Tests for the ResponseCache service and orchestrator integration."""

from unittest.mock import AsyncMock, patch

import pytest

from services.cache.response_cache import ResponseCache
from services.orchestrator import Orchestrator

pytestmark = pytest.mark.unit


def test_response_cache_build_cache_key_stability():
    """Same parameters always produce the same key."""
    cache = ResponseCache(enable_persistence=False)
    key1 = cache.build_cache_key("Hello world", "student", "beginner", 3, "study")
    key2 = cache.build_cache_key("Hello world", "student", "beginner", 3, "study")
    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex


def test_response_cache_build_cache_key_normalization():
    """Case and extra whitespace are normalized in the key."""
    cache = ResponseCache(enable_persistence=False)
    key1 = cache.build_cache_key("Hello World", "student", "beginner", 3, "study")
    key2 = cache.build_cache_key("  hello world  ", "student", "beginner", 3, "study")
    assert key1 == key2


def test_response_cache_get_and_set():
    """Cache stores and retrieves entries with TTL."""
    cache = ResponseCache(enable_persistence=False)
    cache.set("query", "answer", metadata={"intent": "study"}, ttl_seconds=60)
    assert cache.get("query") == "answer"
    assert cache.get_entry("query").metadata["intent"] == "study"


def test_response_cache_expired_entry_is_miss():
    """Expired entries are treated as cache misses."""
    import time

    cache = ResponseCache(enable_persistence=False)
    cache.set("query", "answer", ttl_seconds=1)
    time.sleep(1.1)
    assert cache.get("query") is None


def test_response_cache_invalidate_all():
    """invalidate_all clears every entry."""
    cache = ResponseCache(enable_persistence=False)
    cache.set("q1", "a1")
    cache.set("q2", "a2")
    assert cache.size() == 2
    removed = cache.invalidate_all()
    assert removed == 2
    assert cache.size() == 0


def test_response_cache_stats():
    """Stats track hits and misses."""
    cache = ResponseCache(enable_persistence=False)
    cache.set("q1", "a1")
    cache.get("q1")
    cache.get("missing")
    stats = cache.get_stats()
    assert stats.total_hits == 1
    assert stats.total_misses == 1
    assert stats.total_sets == 1


@pytest.mark.anyio
async def test_orchestrator_cache_hit_returns_cached_answer(db_session):
    """A cache hit bypasses LMS and LLM and returns the stored response."""
    message = "Какие дедлайны?"
    role = "active_student"
    cached_answer = "Дедлайн: 2026-08-05"
    cache = ResponseCache(enable_persistence=False)
    intent = Orchestrator.detect_intent(message)
    cache_key = cache.build_cache_key(message, role, "beginner", 3, intent)
    cache.set_by_key(
        cache_key,
        query=message,
        response=cached_answer,
        metadata={
            "sources": [{"type": "lms", "title": "ДЗ: Пример"}],
            "intent": intent,
            "model": None,
            "latency_ms": 0,
            "error": None,
        },
    )

    orchestrator = Orchestrator(db_session, cache=cache)
    result = await orchestrator.process(
        message=message,
        role=role,
        difficulty="beginner",
        course_id=3,
    )
    assert result["answer"] == cached_answer
    assert result["cache_hit"] is True
    assert result["intent"] == intent


@pytest.mark.anyio
async def test_orchestrator_cache_miss_saves_result(db_session):
    """A cache miss executes the pipeline and stores the result."""
    from datetime import datetime, timezone
    from adapters.lms_adapter import Deadline

    message = "Какие дедлайны?"
    role = "active_student"
    deadline = Deadline(
        id=1,
        course_id=3,
        module_id=10,
        instance_id=1,
        name="ДЗ: Пример",
        modname="assign",
        due_date=datetime(2026, 8, 5, 18, 49, 57, tzinfo=timezone.utc),
        url="https://lms.example.com/mod/assign/view.php?id=10",
    )

    cache = ResponseCache(enable_persistence=False)
    orchestrator = Orchestrator(db_session, cache=cache)

    with patch(
        "services.orchestrator.lms_adapter.get_courses",
        new=AsyncMock(return_value=[type("C", (), {"id": 3, "fullname": "Test", "shortname": "test"})()]),
    ), patch(
        "services.orchestrator.lms_adapter.get_course_deadlines",
        new=AsyncMock(return_value=[deadline]),
    ), patch(
        "services.orchestrator.lms_adapter.get_user_course_progress",
        new=AsyncMock(return_value={"user_id": 3, "course_id": 3, "completion_status": "in_progress", "grade_items": []}),
    ), patch(
        "services.orchestrator.lms_adapter.get_course_contents",
        new=AsyncMock(return_value=[]),
    ):
        result = await orchestrator.process(
            message=message,
            role=role,
            difficulty="beginner",
            course_id=3,
        )

    assert result["cache_hit"] is False
    assert "2026-08-05" in result["answer"]
    assert result["intent"] == "deadline"

    # Second identical request should hit the cache.
    result2 = await orchestrator.process(
        message=message,
        role=role,
        difficulty="beginner",
        course_id=3,
    )
    assert result2["cache_hit"] is True
    assert result2["answer"] == result["answer"]
