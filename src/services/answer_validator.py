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
    refusal: bool = False


class AnswerValidator:
    """Validate LLM answer against safety and quality rules."""

    FORBIDDEN_PATTERNS = [
        r"оценка\s*[:=]?\s*[0-9]+",
        r"ставлю\s+оценку",
        r"выстав[лю]\s+(оценку|зач[её]т)",
        r"измен[ию]\s+(дедлайн|задание|расписание)",
        r"перенес[у]\s+дедлайн",
        r"удал[ию]\s+(задание|курс|модуль)",
    ]

    REFUSAL_REQUEST_PATTERNS = [
        (r"выстав[ьи].*оценк|зач[её]т|оценк.*выстав|постав[ьи].*оценк|выведи.*оценк", "оценки"),
        (r"перенес[и].*дедлайн|измен[и].*дедлайн|дедлайн.*перенес|продли.*дедлайн|сдвин[ьи].*дедлайн", "дедлайны"),
    ]

    # Markdown links that look like [text](number) — LLM sometimes generates fake KB links
    FAKE_KB_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\s*\((\d+)\)")

    # Phrases that indicate the LLM itself is refusing / has insufficient data.
    REFUSAL_ANSWER_PHRASES = [
        r"у меня недостаточно данных",
        r"обратитесь к преподавателю",
        r"не могу ответить",
        r"не располагаю данными",
    ]

    def __init__(
        self,
        answer: str,
        sources: List[Dict[str, Any]],
        has_lms_or_rag_context: bool,
        user_message: Optional[str] = None,
    ):
        self.answer = answer
        self.sources = sources
        self.has_context = has_lms_or_rag_context
        self.user_message = (user_message or "").lower()
        self.issues: List[str] = []

    @staticmethod
    def requires_refusal(message: str) -> Optional[str]:
        """Return refusal topic if the user message requires an explicit refusal.

        This is used by the orchestrator for an early short-circuit before
        calling the LLM or any external systems.
        """
        lower = message.lower()
        for pattern, topic in AnswerValidator.REFUSAL_REQUEST_PATTERNS:
            if re.search(pattern, lower):
                return topic
        return None

    def _check_refusal_requests(self) -> None:
        """Detect user requests that should be refused explicitly.

        This checks the original user message, not the LLM answer, so refusals
        are deterministic and do not depend on whether the LLM happened to
        produce a fallback or a weak answer.
        """
        topic = self.requires_refusal(self.user_message)
        if topic:
            self.issues.append(f"Запрос требует отказа: {topic}.")

    def validate(self) -> ValidationResult:
        """Run validation rules and return normalized result."""
        self._check_empty()
        self._check_forbidden_actions()
        self._check_refusal_requests()
        self._check_refusal_answer()
        self._check_sources()

        if self.issues:
            # If the issue is a refusal request, replace with an explicit refusal.
            refusal_topics = {topic for _, topic in self.REFUSAL_REQUEST_PATTERNS}
            refusal_answer = None
            for issue in self.issues:
                for topic in refusal_topics:
                    if topic in issue:
                        refusal_answer = (
                            "Я не выставляю оценки и не изменяю учебный процесс. "
                            "Обратитесь к преподавателю."
                        )
                        break
                if refusal_answer:
                    break

            if not refusal_answer and any(
                "содержит отказ" in issue or "недостаток данных" in issue
                for issue in self.issues
            ):
                refusal_answer = (
                    "У меня недостаточно данных, чтобы точно ответить. "
                    "Обратитесь к преподавателю."
                )

            if refusal_answer:
                return ValidationResult(
                    is_valid=True,
                    answer=refusal_answer,
                    issues=[],
                    fallback=False,
                    refusal=True,
                )

            fallback_answer = self.sanitize_answer()
            # If sanitized answer still has meaningful content and sources, use it instead of generic fallback
            if (
                len(fallback_answer.strip()) > 30
                and not self.FAKE_KB_LINK_PATTERN.search(fallback_answer)
                and self.sources
            ):
                return ValidationResult(
                    is_valid=True,
                    answer=fallback_answer,
                    issues=self.issues,
                    fallback=False,
                )
            return ValidationResult(
                is_valid=False,
                answer=self._build_fallback(),
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

    def _is_refusal_answer(self) -> bool:
        lower = self.answer.lower()
        return any(re.search(pattern, lower) for pattern in self.REFUSAL_ANSWER_PHRASES)

    def _check_refusal_answer(self) -> None:
        """Detect when the LLM itself produced a refusal/insufficient-data answer."""
        if self._is_refusal_answer():
            self.issues.append("Ответ LLM сам содержит отказ/недостаток данных.")

    def _check_sources(self) -> None:
        # If the LLM produced a refusal, we intentionally do not require sources.
        if self._is_refusal_answer():
            return
        if self.has_context and not self.sources:
            self.issues.append("Ответ не содержит источников, хотя контекст есть.")
        # Detect self-generated fake KB links like [Фрагмент 1](84)
        if self.FAKE_KB_LINK_PATTERN.search(self.answer):
            self.issues.append("Ответ содержит самодельные markdown-ссылки на KB вместо предоставленных источников.")

    def sanitize_answer(self) -> str:
        """Remove or normalize fake markdown links generated by LLM."""
        # Replace [text](number) with plain text, keeping the label
        sanitized = self.FAKE_KB_LINK_PATTERN.sub(r"\1", self.answer)
        return sanitized

    def _build_fallback(self) -> str:
        return (
            "Я не смог сформировать надёжный ответ на ваш вопрос. "
            "Пожалуйста, переформулируйте запрос или обратитесь к преподавателю."
        )
