"""Tests for Orchestrator deterministic answer builders."""

import pytest

from services.orchestrator import Orchestrator

pytestmark = pytest.mark.unit


def _make_progress(sections):
    return {
        "completion_status": "in_progress",
        "overall_grade_formatted": "-",
        "grade_items": [],
        "activity_completions": [],
    }


def test_build_deadline_answer_respects_max_lms_deadlines():
    """Deadline short-circuit must list exactly max_lms_deadlines items."""
    lms_data = {
        "deadlines": [
            {"id": i, "name": f"ДЗ {i}", "due_date": f"2026-08-{10 + i:02d}", "url": f"#d{i}"}
            for i in range(1, 11)
        ],
        "contents": [],
    }

    answer, sources = Orchestrator._build_deadline_answer(
        "Когда дедлайны?", lms_data, course_id=3, max_lms_deadlines=3
    )
    assert answer.count("ДЗ ") == 3
    assert len(sources) == 3


def test_build_deadline_answer_default_limit_is_five():
    """When no limit is passed, the legacy default of 5 deadlines is used."""
    lms_data = {
        "deadlines": [
            {"id": i, "name": f"ДЗ {i}", "due_date": f"2026-08-{10 + i:02d}", "url": f"#d{i}"}
            for i in range(1, 11)
        ],
        "contents": [],
    }

    answer, sources = Orchestrator._build_deadline_answer(
        "Когда дедлайны?", lms_data, course_id=3
    )
    assert answer.count("ДЗ ") == 5
    assert len(sources) == 5


def test_build_progress_answer_limits_all_modules():
    """Progress answer must list at most max_lms_contents modules."""
    contents = [
        {"id": i, "section_name": f"Раздел {i:02d}", "name": f"Урок {i}", "modname": "page", "url": f"#u{i}"}
        for i in range(1, 21)
    ]
    lms_data = {
        "progress": _make_progress([]),
        "contents": contents,
    }

    answer, _ = Orchestrator._build_progress_answer(
        "Перечисли модули курса", lms_data, course_id=3, max_lms_contents=7
    )
    assert answer.count("Раздел ") == 7


def test_build_progress_answer_default_module_limit():
    """When no limit is passed, the config default of 12 modules is used."""
    contents = [
        {"id": i, "section_name": f"Раздел {i:02d}", "name": f"Урок {i}", "modname": "page", "url": f"#u{i}"}
        for i in range(1, 31)
    ]
    lms_data = {
        "progress": _make_progress([]),
        "contents": contents,
    }

    answer, _ = Orchestrator._build_progress_answer(
        "Перечисли модули курса", lms_data, course_id=3
    )
    assert answer.count("Раздел ") == 12


def test_build_organizational_count_answer_assignments():
    """Count questions about assignments return exact number from LMS contents."""
    contents = [
        {"id": i, "section_name": "Модуль 1", "name": f"ДЗ: Task {i}", "modname": "assign", "url": f"#a{i}"}
        for i in range(1, 16)
    ]
    lms_data = {"contents": contents}

    answer, sources = Orchestrator._build_organizational_count_answer(
        "Сколько всего заданий в курсе?", lms_data, course_id=4
    )
    assert "15 заданий" in answer
    assert answer.count("ДЗ: Task") == 15
    assert len(sources) == 15


def test_build_organizational_count_answer_modules():
    """Count questions about modules return exact number of unique sections."""
    contents = [
        {"id": 1, "section_name": "Модуль 1", "name": "Урок 1", "modname": "page", "url": "#1"},
        {"id": 2, "section_name": "Модуль 1", "name": "Урок 2", "modname": "page", "url": "#2"},
        {"id": 3, "section_name": "Модуль 2", "name": "Урок 3", "modname": "page", "url": "#3"},
    ]
    lms_data = {"contents": contents}

    answer, _ = Orchestrator._build_organizational_count_answer(
        "Сколько модулей в курсе?", lms_data, course_id=4
    )
    assert "2 модуля" in answer


def test_build_organizational_count_answer_no_contents():
    """When LMS has no contents, count answer returns empty-course message."""
    answer, sources = Orchestrator._build_organizational_count_answer(
        "Сколько заданий?", {"contents": []}, course_id=4
    )
    assert "В курсе пока нет" in answer
    assert sources == []


def test_extract_course_mentions_filters_non_course_starters():
    """Course mentions starting with non-course starters are ignored."""
    starters = {"какой", "сколько", "что"}
    mentions = Orchestrator._extract_course_mentions(
        'Расскажи про курс "Какой-нибудь"', non_course_starters=starters
    )
    assert "Какой-нибудь" not in mentions


def test_extract_course_mentions_allows_real_course_names():
    """Real course names are extracted even with a starter list configured."""
    starters = {"какой", "сколько"}
    mentions = Orchestrator._extract_course_mentions(
        'Расскажи про курс "Промпт-инжиниринг"', non_course_starters=starters
    )
    assert "Промпт-инжиниринг" in mentions


def test_build_progress_answer_uses_fallback_for_no_progress():
    """When no modules are completed, configured fallback is used."""
    contents = [
        {"id": 1, "section_name": "Модуль 1", "name": "Урок 1", "modname": "page", "url": "#1"},
    ]
    lms_data = {
        "progress": _make_progress([]),
        "contents": contents,
    }
    fallback = {"no_lms_data": "TEST_FALLBACK_LMS"}

    answer, _ = Orchestrator._build_progress_answer(
        "Какие модули я уже прошёл?", lms_data, course_id=3,
        fallback_messages=fallback,
    )
    assert "TEST_FALLBACK_LMS" in answer
