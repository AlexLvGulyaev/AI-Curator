"""Answer validator for AI Curator LLM responses."""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    """Result of answer validation."""

    is_valid: bool
    answer: str
    issues: List[str]
    fallback: bool = False


class AnswerValidator:
    """Validate LLM answer against safety and quality rules."""

    FORBIDDEN_PATTERNS = [
        r"оценка\s*[:=]?\s*[0-9]+",
        r"ставлю\s+оценку",
        r"измен[ию]\s+(дедлайн|задание|расписание)",
        r"удал[ию]\s+(задание|курс|модуль)",
    ]

    def __init__(self, answer: str, sources: List[Dict[str, Any]], has_lms_or_rag_context: bool):
        self.answer = answer
        self.sources = sources
        self.has_context = has_lms_or_rag_context
        self.issues: List[str] = []

    def validate(self) -> ValidationResult:
        """Run validation rules and return normalized result."""
        self._check_empty()
        self._check_forbidden_actions()
        self._check_sources()

        if self.issues:
            fallback_answer = self._build_fallback()
            return ValidationResult(
                is_valid=False,
                answer=fallback_answer,
                issues=self.issues,
                fallback=True,
            )

        return ValidationResult(
            is_valid=True,
            answer=self.answer,
            issues=[],
        )

    def _check_empty(self) -> None:
        if not self.answer or not self.answer.strip():
            self.issues.append("Ответ пустой.")

    def _check_forbidden_actions(self) -> None:
        lower = self.answer.lower()
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, lower):
                self.issues.append(f"Ответ содержит запрещённое действие: {pattern}")

    def _check_sources(self) -> None:
        if self.has_context and not self.sources:
            self.issues.append("Ответ не содержит источников, хотя контекст есть.")

    def _build_fallback(self) -> str:
        return (
            "Я не смог сформировать надёжный ответ на ваш вопрос. "
            "Пожалуйста, переформулируйте запрос или обратитесь к преподавателю."
        )
