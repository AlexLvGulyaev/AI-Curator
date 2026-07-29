"""Tests for deadline and progress endpoints."""

import pytest

from adapters.lms_adapter import MoodleLMSAdapter


@pytest.mark.asyncio
async def test_get_course_deadlines():
    adapter = MoodleLMSAdapter()
    deadlines = await adapter.get_course_deadlines(3)
    assert isinstance(deadlines, list)
    assert len(deadlines) == 9, "Expected 9 assignment deadlines"
    for deadline in deadlines:
        assert deadline.course_id == 3
        assert deadline.modname == "assign"
        assert deadline.due_date is not None


@pytest.mark.asyncio
async def test_get_user_course_progress():
    adapter = MoodleLMSAdapter()
    progress = await adapter.get_user_course_progress(3, 3)
    assert progress.user_id == 3
    assert progress.course_id == 3
    assert progress.user_fullname == "Student Demo"
    assert len(progress.grade_items) > 0
