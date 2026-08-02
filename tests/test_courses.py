"""Tests for the LMS Adapter courses methods."""

import pytest

from adapters.lms_adapter import MoodleLMSAdapter

pytestmark = pytest.mark.integration


@pytest.mark.anyio
async def test_get_courses():
    adapter = MoodleLMSAdapter()
    courses = await adapter.get_courses()
    assert isinstance(courses, list)
    assert len(courses) >= 1
    target = [c for c in courses if c.shortname == "claude-code-express"]
    assert target, "Expected demo course to be present in Moodle"


@pytest.mark.anyio
async def test_get_course_contents():
    adapter = MoodleLMSAdapter()
    modules = await adapter.get_course_contents(3)
    assert isinstance(modules, list)
    assert len(modules) > 0
    assign_modules = [m for m in modules if m.modname == "assign"]
    assert len(assign_modules) == 9, "Expected 9 assignments in the demo course"


@pytest.mark.anyio
async def test_health_check():
    adapter = MoodleLMSAdapter()
    health = await adapter.health_check()
    assert health.status == "ok"
    assert health.response_time_ms is not None
