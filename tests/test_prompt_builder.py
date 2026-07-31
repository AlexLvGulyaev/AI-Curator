"""Tests for PromptBuilder."""

from services.prompt_builder import PromptBuilder


def test_prompt_builder_uses_orchestrator_context_limits():
    """PromptBuilder trims LMS contents and deadlines according to orchestrator config."""
    class FakeAiConfig:
        system_prompt = "System"
        beginner_instructions = "Beginner"
        advanced_instructions = "Advanced"
        few_shot_examples = None
        output_rules = None
        max_history_messages = 6

    class FakeOrchestratorConfig:
        max_lms_contents = 2
        max_lms_deadlines = 1

    lms_data = {
        "contents": [
            {"section_name": "Модуль 1", "name": "Урок 1", "modname": "page", "url": "#1"},
            {"section_name": "Модуль 1", "name": "Урок 2", "modname": "page", "url": "#2"},
            {"section_name": "Модуль 2", "name": "Урок 3", "modname": "page", "url": "#3"},
        ],
        "deadlines": [
            {"name": "ДЗ 1", "due_date": "2026-08-01", "url": "#d1"},
            {"name": "ДЗ 2", "due_date": "2026-08-02", "url": "#d2"},
        ],
    }

    builder = PromptBuilder(FakeAiConfig(), orchestrator_config=FakeOrchestratorConfig())
    prompt = builder.build("Сколько уроков?", lms_data=lms_data)

    assert prompt.count("Урок 1") == 1
    assert prompt.count("Урок 2") == 1
    assert "Урок 3" not in prompt
    assert prompt.count("ДЗ 1") == 1
    assert "ДЗ 2" not in prompt


def test_prompt_builder_fallback_limits():
    """PromptBuilder uses default limits when orchestrator config is absent."""
    class FakeAiConfig:
        system_prompt = "System"
        beginner_instructions = "Beginner"
        advanced_instructions = "Advanced"
        few_shot_examples = None
        output_rules = None
        max_history_messages = 6

    lms_data = {
        "contents": [{"section_name": "M", "name": f"Урок {i}", "modname": "page", "url": f"#{i}"} for i in range(25)],
        "deadlines": [{"name": f"ДЗ {i}", "due_date": "2026-08-01", "url": f"#d{i}"} for i in range(10)],
    }

    builder = PromptBuilder(FakeAiConfig())
    prompt = builder.build("Сколько уроков?", lms_data=lms_data)

    # Default limits are 12 contents and 5 deadlines.
    assert prompt.count("Урок 11") == 1
    assert "Урок 12" not in prompt
    assert prompt.count("ДЗ 4") == 1
    assert "ДЗ 5" not in prompt
