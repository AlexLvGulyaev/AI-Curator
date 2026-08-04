"""Orchestrator for AI Curator chat: classify, gather context, generate answer."""

import asyncio
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.lms_adapter import lms_adapter
from config import settings
from services.ai_config import AiConfigService
from services.answer_validator import AnswerValidator
from services.cache.response_cache import ResponseCache, response_cache
from services.llm_adapter import LLMAdapter, LlmResponse
from services.logger import LoggerService
from services.orchestrator_config import OrchestratorConfigService
from services.prompt_builder import PromptBuilder
from services.rag_pipeline import RagPipeline
from services.retrieval_tuning import RetrievalTuningService


class OrchestratorError(Exception):
    """Base exception for orchestration failures."""

    pass


class Orchestrator:
    """End-to-end chat orchestrator."""

    # Demo role -> user context mapping. In production this comes from auth/session.
    ROLE_CONFIG: Dict[str, Dict[str, Any]] = {
        "active_student": {"user_id": 10, "course_ids": [3, 4], "default_course_id": 3},
        "late_student": {"user_id": 11, "course_ids": [3], "default_course_id": 3},
        "new_student": {"user_id": 12, "course_ids": [3], "default_course_id": 3},
        # Legacy fallback for old Web UI without explicit role mapping
        "student_demo": {"user_id": 3, "course_ids": [3, 4], "default_course_id": 3},
    }

    ORG_KEYWORDS = [
        "дедлайн",
        "дедлайны",
        "срок",
        "сдача",
        "задание",
        "задания",
        "когда",
        "до когда",
        "прогресс",
        "оценка",
        "оценки",
        "зачёт",
        "зачет",
        "сколько осталось",
        "сколько",
        "количество",
        "урок",
        "уроки",
        "модуль",
        "модули",
        "содержание курса",
        "структура курса",
        "программа курса",
        "темы курса",
        "содержание",
        "структура",
        "расписание",
        "перенеси",
        "продли",
        "измени",
    ]
    STUDY_KEYWORDS = [
        "лекция",
        "лекции",
        "методичка",
        "инструкция",
        "объясни",
        "расскажи",
        "как работает",
        "что такое",
        "help",
        "помоги",
        "раскрой",
        "опиши",
        "в чем суть",
        "из чего состоит",
        "разница",
        "сравни",
        "примеры",
    ]
    PROGRESS_KEYWORDS = [
        "прошёл",
        "прошел",
        "завершил",
        "сдал",
        "выполнил",
        "уже сделал",
        "мой прогресс",
        "мои результаты",
        "какие модули",
        "какие задания",
    ]

    def __init__(self, db: AsyncSession, cache: ResponseCache = response_cache):
        self.db = db
        self.logger = LoggerService(db)
        self.tracer = self.logger.tracer
        self.ai_config_service = AiConfigService(db)
        self.orchestrator_config_service = OrchestratorConfigService(db)
        self._ocfg: dict = {}
        self.response_cache = cache

    @staticmethod
    def _execution_mode_from_sources(need_lms: bool, need_rag: bool) -> str:
        """Return route source mode based on intent source flags."""
        if need_lms and need_rag:
            return "mixed"
        if need_lms:
            return "lms"
        if need_rag:
            return "rag"
        return "text"

    async def _finish_execution(
        self,
        exec_session_id: int,
        request: Any,
        steps: List[Dict[str, Any]],
        status: str,
        duration_ms: float,
        execution_metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist execution steps, link request and close the session."""
        await self.tracer.update_execution_session(
            exec_session_id, request_id=request.id
        )
        if steps:
            await self.tracer.add_execution_steps(exec_session_id, steps)
        await self.tracer.finish_execution_session(
            exec_session_id,
            status,
            duration_ms=int(duration_ms) if duration_ms is not None else None,
            execution_metadata=execution_metadata,
        )

    def _save_cache_result(
        self,
        message: str,
        result: Dict[str, Any],
        cache_key: str,
        ttl_seconds: Optional[int],
    ) -> Dict[str, Any]:
        """Persist a successful result to the response cache.

        Errors and explicit error intents are not cached. The helper is
        synchronous because cache persistence is a single small JSON write.
        """
        if result.get("intent") == "error" or result.get("error"):
            return result
        self.response_cache.set_by_key(
            cache_key,
            query=message,
            response=result["answer"],
            metadata={
                "sources": result.get("sources", []),
                "intent": result.get("intent"),
                "model": result.get("model"),
                "latency_ms": result.get("latency_ms"),
                "error": result.get("error"),
            },
            ttl_seconds=ttl_seconds,
        )
        return result

    def _non_course_starters(self) -> set:
        """Return common Russian sentence starters that are NOT course names."""
        return set(getattr(self, "_ocfg", {}).get("non_course_starters", []))

    @staticmethod
    def _extract_course_mentions(
        message: str,
        non_course_starters: Optional[set] = None,
    ) -> List[str]:
        """Extract potential course names from the user message.

        Conservative heuristics:
        - quoted strings only when they are preceded by a course marker ("курс");
        - explicit "курс X" / "по курсу X" patterns;
        - short capitalized phrases after "курс Name".

        Assignment and module names quoted in questions like
        "Что повторить перед заданием \"Ролевые промпты\"" are intentionally
        excluded so they do not trigger a "course not found" refusal.

        `non_course_starters` filters out course-like phrases whose first word
        is a common question starter ("какой", "сколько", etc.) configured by
        methodologists in the orchestrator console.
        """
        starters = non_course_starters or set()
        mentions = []

        def _first_word_in_starters(candidate: str) -> bool:
            if not candidate:
                return False
            words = candidate.split()
            if not words:
                return False
            first_word = words[0].lower()
            # Strip only complete Russian question/particle suffixes such as
            # -нибудь / -либо / -то. re.sub with word boundaries avoids
            # deleting individual characters that happen to be in the suffix.
            first_word = re.sub(r"(-нибудь|-либо|-то)$", "", first_word)
            return first_word in starters

        # Quoted strings are course names only if preceded by a course marker.
        for match in re.finditer(
            r'курс[аеуом]?\s+["«"]([^"""]+)["""]',
            message,
            re.IGNORECASE,
        ):
            candidate = match.group(1).strip()
            if _first_word_in_starters(candidate):
                continue
            mentions.append(candidate)

        # Capture "по курсу Name" / "курс Name" where Name is a short proper noun.
        # This is much more reliable than scanning the whole sentence.
        # We search case-insensitively for the marker but require the captured
        # name to start with an uppercase letter in the original text. A single
        # lowercase conjunction/particle right after "курс" must not match.
        for match in re.finditer(
            r'(?:по\s+)?курс[аеуом]?\s+([А-ЯЁA-Z][а-яёa-zА-ЯЁA-Z0-9\-]*(?:\s+[а-яёa-zА-ЯЁA-Z0-9\-]+){0,2})',
            message,
            re.IGNORECASE,
        ):
            candidate = match.group(1).strip()
            if _first_word_in_starters(candidate):
                continue
            mentions.append(candidate)
        return mentions

    @staticmethod
    def _resolve_role_context(role: Optional[str]) -> Dict[str, Any]:
        """Return demo user_id and available course_ids for a role."""
        if role and role in Orchestrator.ROLE_CONFIG:
            return Orchestrator.ROLE_CONFIG[role]
        # Fallback to legacy student_demo if role is missing/unknown.
        return Orchestrator.ROLE_CONFIG["student_demo"]

    def _set_config(self, ocfg) -> None:
        """Store the effective orchestrator config dict for the request lifetime."""
        self._ocfg = {
            "intent_rules": getattr(ocfg, "intent_rules", {}),
            "default_intent": getattr(ocfg, "default_intent", "study"),
            "intent_source_map": getattr(ocfg, "intent_source_map", {}),
            "non_course_starters": getattr(ocfg, "non_course_starters", []),
            "max_lms_contents": getattr(ocfg, "max_lms_contents", 12),
            "max_lms_deadlines": getattr(ocfg, "max_lms_deadlines", 5),
            "intent_max_tokens": getattr(ocfg, "intent_max_tokens", {}),
            "fallback_messages": getattr(ocfg, "fallback_messages", {}),
        }

    def _intent_keywords(self, intent: str) -> List[str]:
        """Return keywords for an intent from the active config."""
        rules = self._ocfg.get("intent_rules", {})
        return list(rules.get(intent, {}).get("keywords", []))

    def _eval_condition(self, condition: Any, message_lower: str) -> bool:
        """Evaluate a condition entry from intent_rules.

        Supported forms:
        - "is_org" / "is_study" / "is_progress" (bare predicate string)
        - ["is_org"] / ["is_study"] / ["is_progress"]
        - ["has_keyword", ["word1", "word2"]]
        - {"and": [...conditions...]}

        Bare strings inside "and" arrays are normalized to single-element lists
        so the UI can save conditions compactly without breaking evaluation.
        """
        if isinstance(condition, dict) and "and" in condition:
            parts = condition["and"]
            # Normalize bare strings inside "and" to single-element lists.
            normalized_parts = [
                [part] if isinstance(part, str) else part for part in parts
            ]
            return all(self._eval_condition(part, message_lower) for part in normalized_parts)

        # Bare predicate string outside of an "and" block.
        if isinstance(condition, str):
            condition = [condition]

        if not isinstance(condition, (list, tuple)) or not condition:
            return False

        head = condition[0]
        if head in ("is_org", "is_study", "is_progress"):
            intent_map = {
                "is_org": "organizational",
                "is_study": "study",
                "is_progress": "progress",
            }
            keywords = self._intent_keywords(intent_map[head])
            # Fallback for is_org: if organizational has no keywords, use deadline+progress keywords.
            if head == "is_org" and not keywords:
                keywords = self._intent_keywords("deadline") + self._intent_keywords("progress")
            return any(kw in message_lower for kw in keywords)

        if head == "has_keyword" and len(condition) >= 2:
            words = condition[1]
            return any(w.lower() in message_lower for w in words)

        return False

    def _intent_from_conditions(self, message_lower: str) -> Optional[str]:
        """Return the first intent whose conditions match, ordered by priority."""
        rules = self._ocfg.get("intent_rules", {})
        candidates = []
        for intent, rule in rules.items():
            conditions = rule.get("conditions")
            if not conditions:
                continue
            priority = rule.get("priority", 99)
            for cond in conditions:
                if self._eval_condition(cond, message_lower):
                    candidates.append((priority, intent))
                    break
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    async def _get_available_courses(self, course_ids: List[int]) -> List[Dict[str, Any]]:
        """Return LMS course info for the given course ids."""
        try:
            all_courses = await lms_adapter.get_courses()
            return [
                {"id": c.id, "fullname": c.fullname, "shortname": c.shortname}
                for c in all_courses
                if c.id in course_ids
            ]
        except Exception:
            return []

    @staticmethod
    def _find_mentioned_course(
        message: str,
        available_courses: List[Dict[str, Any]],
        non_course_starters: Optional[set] = None,
    ) -> Optional[int]:
        """Return course_id if the message clearly mentions one of available courses."""
        if not available_courses:
            return None
        mentions = Orchestrator._extract_course_mentions(message, non_course_starters)
        message_lower = message.lower()
        for course in available_courses:
            names = [
                course.get("fullname", "").lower(),
                course.get("shortname", "").lower(),
            ]
            for name in names:
                if not name:
                    continue
                # Direct mention
                if name in message_lower:
                    return course["id"]
                # Quoted / capitalized fragment match
                for mention in mentions:
                    if mention.lower() in name or name in mention.lower():
                        return course["id"]
        return None

    @staticmethod
    def _looks_like_other_course(
        message: str,
        available_courses: List[Dict[str, Any]],
        non_course_starters: Optional[set] = None,
    ) -> Optional[str]:
        """Return the mentioned course name if it is not in available courses."""
        if not available_courses:
            return None
        mentions = Orchestrator._extract_course_mentions(message, non_course_starters)
        available_names = [
            (c.get("fullname") or "").lower()
            for c in available_courses
        ] + [
            (c.get("shortname") or "").lower()
            for c in available_courses
        ]
        for mention in mentions:
            mention_lower = mention.lower()
            if any(mention_lower in name or name in mention_lower for name in available_names if name):
                continue
            # Common generic words should not trigger a mismatch.
            if mention_lower in ("этот курс", "данный курс", "текущий курс"):
                continue
            return mention
        return None

    @staticmethod
    def detect_intent(message: str, ocfg: Optional[Dict[str, Any]] = None) -> str:
        """Classify message intent using the provided orchestrator config.

        When `ocfg` is None, falls back to hardcoded defaults so that the
        classifier can be used without a database session (e.g. in tests).
        """
        lower = message.lower()

        def _intent_keywords(intent: str) -> List[str]:
            rules = (ocfg or {}).get("intent_rules", {})
            keywords = list(rules.get(intent, {}).get("keywords", []))
            if keywords:
                return keywords
            # Graceful fallback: when no config (or intent missing from config),
            # use hardcoded keyword sets identical to the original behaviour.
            fallbacks = {
                "deadline": [
                    "дедлайн",
                    "когда сдать",
                    "до когда",
                    "когда нужно сдать",
                    "когда сдавать",
                    "срок сдачи",
                    "срок",
                    "когда deadline",
                ],
                "progress": [
                    "прошёл",
                    "прошел",
                    "завершил",
                    "сдал",
                    "выполнил",
                    "уже сделал",
                    "мой прогресс",
                    "мои результаты",
                    "какие модули",
                    "какие задания",
                ],
                "study": [
                    "лекция",
                    "лекции",
                    "методичка",
                    "инструкция",
                    "объясни",
                    "расскажи",
                    "как работает",
                    "что такое",
                    "help",
                    "помоги",
                    "раскрой",
                    "опиши",
                    "в чем суть",
                    "из чего состоит",
                    "разница",
                    "сравни",
                    "примеры",
                ],
                "organizational": [
                    "дедлайн",
                    "дедлайны",
                    "срок",
                    "сдача",
                    "задание",
                    "задания",
                    "когда",
                    "до когда",
                    "прогресс",
                    "оценка",
                    "оценки",
                    "зачёт",
                    "зачет",
                    "сколько осталось",
                    "сколько",
                    "количество",
                    "урок",
                    "уроки",
                    "модуль",
                    "модули",
                    "содержание курса",
                    "структура курса",
                    "программа курса",
                    "темы курса",
                    "содержание",
                    "структура",
                    "расписание",
                    "перенеси",
                    "продли",
                    "измени",
                ],
            }
            return fallbacks.get(intent, [])

        def _eval_condition(condition):
            if isinstance(condition, dict) and "and" in condition:
                parts = condition["and"]
                normalized_parts = [
                    [part] if isinstance(part, str) else part for part in parts
                ]
                return all(_eval_condition(part) for part in normalized_parts)
            if isinstance(condition, str):
                condition = [condition]
            if not isinstance(condition, (list, tuple)) or not condition:
                return False
            head = condition[0]
            if head in ("is_org", "is_study", "is_progress"):
                intent_map = {
                    "is_org": "organizational",
                    "is_study": "study",
                    "is_progress": "progress",
                }
                keywords = _intent_keywords(intent_map[head])
                if head == "is_org" and not keywords:
                    keywords = _intent_keywords("deadline") + _intent_keywords("progress")
                return any(kw in lower for kw in keywords)
            if head == "has_keyword" and len(condition) >= 2:
                words = condition[1]
                return any(w.lower() in lower for w in words)
            return False

        def _intent_from_conditions() -> Optional[str]:
            rules = (ocfg or {}).get("intent_rules", {})
            candidates = []
            for intent, rule in rules.items():
                conditions = rule.get("conditions")
                if not conditions:
                    continue
                priority = rule.get("priority", 99)
                for cond in conditions:
                    if _eval_condition(cond):
                        candidates.append((priority, intent))
                        break
            if not candidates:
                return None
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        is_deadline = any(kw in lower for kw in _intent_keywords("deadline"))
        is_progress = any(kw in lower for kw in _intent_keywords("progress"))
        is_study = any(kw in lower for kw in _intent_keywords("study"))

        org_keywords = _intent_keywords("organizational")
        if not org_keywords:
            org_keywords = _intent_keywords("deadline") + _intent_keywords("progress")
        is_org = any(kw in lower for kw in org_keywords)

        # Deadline questions need deterministic answer from LMS data.
        if is_deadline:
            return "deadline"
        # Progress questions often overlap with organizational keywords (module/assignment).
        # Treat them as a dedicated intent so we can answer from LMS progress directly.
        if is_progress:
            return "progress"
        # Configured conditions take precedence over simple keyword heuristics. This lets
        # methodologists define mixed/organizational rules via the condition DSL even
        # when no simple keyword overlap triggered is_org / is_study.
        condition_intent = _intent_from_conditions()
        if condition_intent:
            return condition_intent
        if is_org and is_study:
            return "mixed"
        # Pure structure questions ("сколько модулей", "из чего состоит курс") need
        # both LMS contents and KB context to avoid hallucinated module counts.
        if is_org and any(kw in lower for kw in ("модуль", "модули", "структура курса", "из чего состоит курс")):
            return "mixed"
        if is_org:
            return "organizational"
        if is_study:
            return "study"
        # Default to leverage RAG for general course questions.
        return (ocfg or {}).get("default_intent", "study")

    @staticmethod
    def _to_dict_list(items: List[Any]) -> List[Dict[str, Any]]:
        """Convert Pydantic models or dicts to plain dicts."""
        return [m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in items]

    @staticmethod
    def _format_deadlines(deadlines: List[Any]) -> List[Dict[str, Any]]:
        result = []
        for d in deadlines:
            data = d.model_dump() if hasattr(d, "model_dump") else dict(d)
            if data.get("due_date"):
                data["due_date"] = data["due_date"].isoformat() if hasattr(data["due_date"], "isoformat") else data["due_date"]
            result.append(data)
        return result

    @staticmethod
    def _format_progress(progress: Any) -> Dict[str, Any]:
        data = progress.model_dump() if hasattr(progress, "model_dump") else dict(progress)
        return data

    @staticmethod
    def _format_course_contents(contents: List[Any]) -> List[Dict[str, Any]]:
        """Convert CourseModule models to plain dicts with formatted fields."""
        result = []
        for item in contents:
            data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            result.append(data)
        return result

    @staticmethod
    def _deduplicate_sections(contents: List[Dict[str, Any]]) -> List[str]:
        """Return unique, meaningful course section names from LMS contents."""
        raw_sections: List[str] = []
        seen_sections: set = set()
        for item in contents:
            section = (item.get("section_name") or "").strip()
            if not section or section in seen_sections:
                continue
            seen_sections.add(section)
            raw_sections.append(section)

        modules: List[str] = []
        lower_all = [s.lower() for s in raw_sections]
        for section in raw_sections:
            lower = section.lower()
            if lower in ("общее", "general"):
                continue
            if any(other != lower and lower in other for other in lower_all):
                continue
            modules.append(section)
        return modules

    @staticmethod
    def _module_completion_status(
        contents: List[Dict[str, Any]],
        activity_completions: List[Dict[str, Any]],
        grade_items: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Return a status per course section (module).

        A section is "completed" if Moodle reports all of its tracked activities
        as completed. A section is "in_progress" if it is not completed but at
        least one assignment in it has been graded (grade_raw is not None). This
        covers the common case where a student has submitted assignments but has
        not formally "viewed" every content page, so Moodle does not mark the whole
        section as complete. Otherwise it is "not_started".
        """
        completion_by_cmid: Dict[int, bool] = {
            ac.get("cmid"): ac.get("completed", False)
            for ac in activity_completions
            if ac.get("cmid") is not None
        }

        section_activities: Dict[str, set] = {}
        section_graded: Dict[str, bool] = {}
        for item in contents:
            section = (item.get("section_name") or "").strip()
            cmid = item.get("id")
            if not section or cmid is None:
                continue
            section_activities.setdefault(section, set()).add(cmid)

        # Determine which sections have at least one graded assignment.
        graded_cmid_set = {
            gi.get("cmid")
            for gi in grade_items
            if gi.get("cmid") is not None and gi.get("grade_raw") is not None
        }
        for item in contents:
            section = (item.get("section_name") or "").strip()
            cmid = item.get("id")
            if section and cmid in graded_cmid_set:
                section_graded[section] = True

        result: Dict[str, str] = {}
        for section, cmids in section_activities.items():
            if not cmids:
                result[section] = "not_started"
                continue
            statuses = [completion_by_cmid.get(cmid, False) for cmid in cmids]
            if all(statuses):
                result[section] = "completed"
            elif section_graded.get(section):
                result[section] = "in_progress"
            elif any(statuses):
                result[section] = "in_progress"
            else:
                result[section] = "not_started"
        return result

    @staticmethod
    def _build_organizational_count_answer(
        message: str,
        lms_data: Dict[str, Any],
        course_id: int,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Build a deterministic answer for count questions from LMS data.

        Questions like "сколько заданий/модулей/уроков в курсе" do not need an
        LLM: the answer is already present in lms_data. Returning a computed
        count eliminates LLM arithmetic hallucinations and makes the setting
        max_lms_contents irrelevant for this family of questions.
        """
        contents = lms_data.get("contents", []) or []
        message_lower = message.lower()

        # What is being counted? Use prefixes because Russian inflections differ.
        asks_assignments = any(message_lower.startswith(kw) or kw in message_lower for kw in ("задание", "задания", "дз", "домашн"))
        asks_modules = any(kw in message_lower for kw in ("модул", "модули"))
        asks_lessons = any(kw in message_lower for kw in ("урок", "уроки"))
        # Default to assignments if the question is generic.

        section_names: List[str] = []
        seen_sections: set = set()
        for item in contents:
            section = (item.get("section_name") or "").strip()
            if section and section not in seen_sections:
                seen_sections.add(section)
                section_names.append(section)

        if asks_modules:
            count = len(section_names)
            items = section_names
        elif asks_lessons:
            items = [
                item.get("name", "Без названия")
                for item in contents
                if (item.get("modname") or "").lower() in ("page", "lesson", "resource", "url")
            ]
            count = len(items)
        else:
            # Count assignments (modname == assign) by default.
            items = [
                item.get("name", "Без названия")
                for item in contents
                if (item.get("modname") or "").lower() == "assign"
            ]
            count = len(items)

        if count == 0:
            body = "В курсе пока нет опубликованных элементов для подсчёта."
            return body, []

        def _plural_form(n: int, forms: tuple[str, str, str]) -> str:
            if n % 10 == 1 and n % 100 != 11:
                return forms[0]
            if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
                return forms[1]
            return forms[2]

        if asks_modules:
            count_word = _plural_form(count, ("{n} модуль", "{n} модуля", "{n} модулей")).format(n=count)
        elif asks_lessons:
            count_word = _plural_form(count, ("{n} урок", "{n} урока", "{n} уроков")).format(n=count)
        else:
            count_word = _plural_form(count, ("{n} задание", "{n} задания", "{n} заданий")).format(n=count)

        lines = [f"В курсе {count_word}:", ""]
        for name in items[:50]:
            lines.append(f"- {name}")

        # Build sources from the listed items.
        sources: List[Dict[str, Any]] = []
        seen_source_titles: set = set()
        for item in contents:
            title = item.get("name")
            if title in items[:50] and title not in seen_source_titles:
                seen_source_titles.add(title)
                sources.append({
                    "type": "lms",
                    "title": title,
                    "url": item.get("url"),
                    "module": item.get("section_name"),
                })

        return "\n".join(lines), sources

    @staticmethod
    def _build_progress_answer(
        message: str,
        lms_data: Dict[str, Any],
        course_id: int,
        max_lms_contents: int = 12,
        fallback_messages: Optional[Dict[str, str]] = None,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Build a deterministic answer for progress-related questions."""
        progress = lms_data.get("progress", {}) or {}
        contents = lms_data.get("contents", []) or []
        completion_status = progress.get("completion_status", "in_progress")
        no_lms_data_template = (fallback_messages or {}).get("no_lms_data")

        # Grade items for assignments and module completion.
        grade_items = progress.get("grade_items", []) or []

        modules = Orchestrator._deduplicate_sections(contents)
        module_statuses = Orchestrator._module_completion_status(
            contents, progress.get("activity_completions", []), grade_items
        )

        # Assignments among grade items.
        assignments = [gi for gi in grade_items if gi.get("item_module") == "assign"]
        graded = [gi for gi in assignments if gi.get("grade_raw") is not None]

        # Overall grade summary.
        grade = progress.get("overall_grade_formatted")
        grade_line = f" Общая оценка: {grade}." if grade and grade != "-" else ""

        lower_message = message.lower()
        asks_completed_modules = any(kw in lower_message for kw in ("прошёл", "прошел", "завершил", "сдал"))
        asks_all_modules = any(kw in lower_message for kw in ("модуль", "модули", "из чего состоит", "структура"))
        asks_assignments = any(kw in lower_message for kw in ("задание", "задания", "сдал", "выполнил"))

        # Lead with concrete completed assignments when available,
        # because that is more informative than a vague "in_progress" status.
        if graded:
            body = "Вы уже сдали:\n" + "\n".join(
                f"- {gi.get('name', 'Задание')}: {gi.get('grade_formatted') or gi.get('gradeformatted', '-')}" for gi in graded
            )
        elif completion_status == "completed":
            body = f"Вы завершили курс.{grade_line}"
        elif completion_status == "no_data":
            body = "У меня нет данных о вашем прогрессе в этом курсе."
        else:
            body = f"Вы пока находитесь в процессе прохождения курса.{grade_line}"

        # List completed modules when the user asks which modules they have passed.
        if asks_completed_modules and modules:
            completed_modules = [m for m in modules if module_statuses.get(m) == "completed"]
            in_progress_modules = [m for m in modules if module_statuses.get(m) == "in_progress"]
            lines: List[str] = []
            if completed_modules:
                lines.append("Пройденные модули:")
                lines.extend(f"- {m}" for m in completed_modules)
            if in_progress_modules:
                lines.append("Модули в процессе:")
                lines.extend(f"- {m}" for m in in_progress_modules)
            if not completed_modules and not in_progress_modules:
                if no_lms_data_template:
                    lines.append(no_lms_data_template)
                else:
                    lines.append("Пока нет завершённых модулей.")
            body += "\n\n" + "\n".join(lines)
        # List all modules when the user asks about course structure.
        elif asks_all_modules and modules:
            body += "\n\nМодули курса:\n" + "\n".join(f"- {m}" for m in modules[:max_lms_contents])

        # List graded assignments explicitly when asked, if not already shown.
        if asks_assignments and not graded:
            if assignments:
                body += "\n\nСданные задания:\n" + "\n".join(
                    f"- {gi.get('name', 'Задание')}: {gi.get('grade_formatted') or gi.get('gradeformatted', '-')}" for gi in assignments
                )
            else:
                body += "\n\nПока нет сданных заданий с выставленной оценкой."

        # Build sources: only unique course modules referenced in the answer.
        sources: List[Dict[str, Any]] = []
        seen_source_sections: set = set()
        module_url_map: Dict[str, Optional[str]] = {}
        for item in contents:
            section = (item.get("section_name") or "").strip()
            if section in modules and section not in module_url_map:
                module_url_map[section] = item.get("url")

        for section in modules:
            if section and section in body and section not in seen_source_sections:
                seen_source_sections.add(section)
                sources.append({
                    "type": "lms",
                    "title": section,
                    "url": module_url_map.get(section),
                })

        return body, sources

    @staticmethod
    def _build_deadline_answer(
        message: str,
        lms_data: Dict[str, Any],
        course_id: int,
        max_lms_deadlines: int = 5,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Build a deterministic answer for deadline questions from LMS data."""
        deadlines = lms_data.get("deadlines", []) or []
        contents = lms_data.get("contents", []) or []
        message_lower = message.lower()

        # Extract a quoted assignment name if present.
        quoted_name = None
        for match in re.finditer(r'["«]([^"«»]+)["»]', message):
            quoted_name = match.group(1).strip()
            break

        # Fuzzy match by quoted name or by individual words from the message.
        def _matches(d: Dict[str, Any]) -> bool:
            name = (d.get("name") or "").lower()
            if quoted_name:
                return quoted_name.lower() in name
            query_words = {w for w in re.findall(r"[а-яa-z0-9]+", message_lower) if len(w) > 3}
            return any(w in name for w in query_words)

        matched = [d for d in deadlines if _matches(d)]
        if not matched:
            # Fall back to all course deadlines sorted by date.
            matched = sorted(
                deadlines,
                key=lambda d: d.get("due_date") or "",
            )

        if not matched:
            body = (
                "В курсе пока нет опубликованных заданий с дедлайнами. "
                "Если вы ожидаете увидеть задание, обратитесь к преподавателю."
            )
            return body, []

        lines: List[str] = []
        sources: List[Dict[str, Any]] = []
        seen_ids: set = set()
        for d in matched[:max_lms_deadlines]:
            due = d.get("due_date")
            due_str = due[:10] if due else "не установлен"
            lines.append(f"- «{d.get('name', 'Без названия')}»: {due_str}")
            did = d.get("id") or d.get("module_id")
            if did and did not in seen_ids:
                seen_ids.add(did)
                sources.append({
                    "type": "lms",
                    "title": d.get("name", "Задание"),
                    "url": d.get("url"),
                })
        body = "Дедлайны заданий:\n" + "\n".join(lines)
        return body, sources

    async def process(
        self,
        message: str,
        *,
        role: Optional[str] = None,
        difficulty: Optional[str] = None,
        course_id: Optional[int] = None,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a student message end-to-end and return answer + sources."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Resolve demo user context from role.
        role_context = self._resolve_role_context(role)
        user_id = role_context["user_id"]
        available_course_ids: List[int] = role_context["course_ids"]
        default_course_id: int = role_context["default_course_id"]

        # Start canonical chat session and execution trace.
        chat_session = await self.logger.create_or_update_chat_session(
            session_id=session_id,
            user_id=user_id,
            role=role,
            course_id=default_course_id,
            difficulty=difficulty,
            mode="text",
        )
        exec_session = await self.tracer.start_execution_session(
            chat_session.id,
            client_ip=client_ip,
            user_agent=user_agent,
            provider_key="openai",
            model_name=None,
        )
        execution_steps: List[Dict[str, Any]] = []

        try:
            result = await self._process_core(
                message=message,
                role=role,
                difficulty=difficulty,
                course_id=course_id,
                session_id=session_id,
                chat_session=chat_session,
                exec_session=exec_session,
                execution_steps=execution_steps,
                user_id=user_id,
                available_course_ids=available_course_ids,
                default_course_id=default_course_id,
                history=history,
            )
            result.setdefault("cache_hit", False)
            return result
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            import traceback
            traceback_text = traceback.format_exc()
            execution_steps.append({
                "stage_name": "error_handler",
                "step_order": 99,
                "duration_ms": 0,
                "step_metadata": {"error": error_text, "traceback": traceback_text},
            })
            fallback_answer = (
                "Произошла внутренняя ошибка. Попробуйте ещё раз позже. "
                "Если проблема повторяется, обратитесь к преподавателю."
            )
            request = await self.logger.create_chat_request(
                session_id=session_id,
                chat_session_id=chat_session.id,
                role=role,
                course_id=course_id if course_id in available_course_ids else default_course_id,
                difficulty=difficulty,
                message=message,
                intent="error",
                lms_calls=[],
                rag_filters={},
            )
            await self.logger.create_chat_log(
                request_id=request.id,
                answer=fallback_answer,
                sources=[],
                llm_model=None,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=0,
                error=traceback_text,
            )
            await self._finish_execution(exec_session.id, request, execution_steps, "error", 0)
            return {
                "answer": fallback_answer,
                "sources": [],
                "intent": "error",
                "model": None,
                "latency_ms": 0,
                "session_id": session_id,
                "cache_hit": False,
                "error": error_text,
            }

    @staticmethod
    def _utc_now() -> datetime:
        """Return current UTC timestamp."""
        return datetime.now(timezone.utc)

    async def _process_core(
        self,
        *,
        message: str,
        role: Optional[str],
        difficulty: Optional[str],
        course_id: Optional[int],
        session_id: str,
        chat_session: Any,
        exec_session: Any,
        execution_steps: List[Dict[str, Any]],
        user_id: int,
        available_course_ids: List[int],
        default_course_id: int,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Core pipeline: classify intent, fetch data, generate and validate answer."""
        t_core_start = time.perf_counter()
        t_core_start_utc = self._utc_now()
        execution_session_status = "ok"

        # Load operational configuration early. Intent classification and the cache
        # decision are cheap and do not require LMS or LLM calls.
        config = await self.ai_config_service.get_active()
        retrieval_tuning = await RetrievalTuningService(self.db).get_or_create_default()
        ocfg = await self.orchestrator_config_service.get_or_create_default()
        self._set_config(ocfg)

        # Early deterministic refusal before any expensive calls.
        refusal_topic = AnswerValidator.requires_refusal(message)
        if refusal_topic:
            refusal = (
                config.refusal_answer_text
                or "Я не выставляю оценки и не изменяю учебный процесс. Обратитесь к преподавателю."
            )
            request = await self.logger.create_chat_request(
                session_id=session_id,
                chat_session_id=chat_session.id,
                role=role,
                course_id=course_id if course_id in available_course_ids else default_course_id,
                difficulty=difficulty,
                message=message,
                intent="refusal",
                lms_calls=[],
                rag_filters={},
            )
            await self.logger.create_chat_log(
                request_id=request.id,
                answer=refusal,
                sources=[],
                llm_model=None,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=0,
                error=None,
            )
            execution_steps.extend([
                {"stage_name": "intent_classify", "step_order": 1, "duration_ms": 0, "step_metadata": {"intent": "refusal", "refusal_topic": refusal_topic}},
                {"stage_name": "response_save", "step_order": 2, "duration_ms": 0},
            ])
            await self._finish_execution(exec_session.id, request, execution_steps, execution_session_status, 0)
            return {
                "answer": refusal,
                "sources": [],
                "intent": "refusal",
                "model": None,
                "latency_ms": 0,
                "session_id": session_id,
                "error": None,
            }

        intent_detect_started_at = self._utc_now()
        t_start = time.perf_counter()
        intent = self.detect_intent(message, ocfg=self._ocfg)
        intent_detect_ms = round((time.perf_counter() - t_start) * 1000, 2)
        intent_detect_finished_at = self._utc_now()
        timings: Dict[str, float] = {
            "intent_detect_ms": intent_detect_ms,
        }
        execution_steps.append({
            "stage_name": "intent_classify",
            "step_order": 1,
            "duration_ms": intent_detect_ms,
            "started_at": intent_detect_started_at,
            "finished_at": intent_detect_finished_at,
            "step_metadata": {"intent": intent},
        })

        # Response cache: identical requests skip LMS/RAG/LLM.
        cache_key = self.response_cache.build_cache_key(message, role, difficulty, course_id, intent)
        effective_cache_ttl = retrieval_tuning.cache_ttl_seconds or settings.cache_ttl_seconds
        cache_entry = None
        if retrieval_tuning.cache_enabled:
            cache_entry = self.response_cache.get_entry_by_key(cache_key)
        if cache_entry:
            # Align canonical session mode with the intent's source route even though
            # the actual answer came from cache.
            source_map = self._ocfg.get("intent_source_map", {})
            intent_sources = source_map.get(intent, {})
            need_lms = bool(
                intent_sources.get("lms", intent in ("organizational", "mixed", "progress", "deadline"))
            )
            need_rag = bool(intent_sources.get("rag", intent in ("study", "mixed")))
            mode = self._execution_mode_from_sources(need_lms, need_rag)
            if mode != chat_session.mode:
                chat_session = await self.logger.create_or_update_chat_session(
                    session_id=session_id,
                    mode=mode,
                )

            cached_result = {
                "answer": cache_entry.response,
                **cache_entry.metadata,
                "cache_hit": True,
                "session_id": session_id,
            }
            request = await self.logger.create_chat_request(
                session_id=session_id,
                chat_session_id=chat_session.id,
                role=role,
                course_id=course_id if course_id in available_course_ids else default_course_id,
                difficulty=difficulty,
                message=message,
                intent=intent,
                lms_calls=[],
                rag_filters={},
            )
            t_core_total_ms = round((time.perf_counter() - t_core_start) * 1000, 2)
            cache_hit_started_at = self._utc_now()
            cache_hit_finished_at = cache_hit_started_at
            response_save_started_at = cache_hit_finished_at
            response_save_finished_at = self._utc_now()
            response_save_ms = max(
                0,
                round((response_save_finished_at - response_save_started_at).total_seconds() * 1000, 2),
            )

            await self.logger.create_chat_log(
                request_id=request.id,
                answer=cached_result["answer"],
                sources=cached_result.get("sources", []),
                llm_model=cached_result.get("model"),
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=t_core_total_ms,
                error=cached_result.get("error"),
                cache_hit=True,
            )
            execution_steps.extend([
                {
                    "stage_name": "cache_hit",
                    "step_order": 2,
                    "duration_ms": 0,
                    "started_at": cache_hit_started_at,
                    "finished_at": cache_hit_finished_at,
                    "step_metadata": {"cache_key": cache_key, "intent": intent},
                },
                {
                    "stage_name": "response_save",
                    "step_order": 3,
                    "duration_ms": response_save_ms,
                    "started_at": response_save_started_at,
                    "finished_at": response_save_finished_at,
                    "step_metadata": {"has_answer": bool(cached_result.get("answer"))},
                },
            ])
            await self._finish_execution(
                exec_session.id,
                request,
                execution_steps,
                execution_session_status,
                t_core_total_ms,
                execution_metadata={"cache_hit": True, "route": "cache", "timings_ms": timings},
            )
            return {**cached_result, "latency_ms": t_core_total_ms}

        # Determine target course: mentioned course in message takes precedence over
        # explicit UI selection, then default, but only if the mentioned course is
        # actually available to this role. Otherwise we refuse.
        available_courses = await self._get_available_courses(available_course_ids)
        non_course_starters = self._non_course_starters()
        mentioned_course_id = self._find_mentioned_course(
            message, available_courses, non_course_starters
        )
        explicit_course_id = course_id if course_id in available_course_ids else None

        # Check whether the user is asking about a course they are not enrolled in.
        other_course = self._looks_like_other_course(
            message, available_courses, non_course_starters
        )
        if other_course:
            out_of_scope_template = self._ocfg.get(
                "fallback_messages", {}
            ).get(
                "out_of_scope_course",
                "У меня нет данных о курсе «{course}» для вашей учётной записи. Обратитесь к преподавателю."
            )
            refusal = out_of_scope_template.format(course=other_course)
            request = await self.logger.create_chat_request(
                session_id=session_id,
                chat_session_id=chat_session.id,
                role=role,
                course_id=explicit_course_id or default_course_id,
                difficulty=difficulty,
                message=message,
                intent="out_of_scope",
                lms_calls=[],
                rag_filters={},
            )
            await self.logger.create_chat_log(
                request_id=request.id,
                answer=refusal,
                sources=[],
                llm_model=None,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=0,
                error=None,
            )
            execution_steps.extend([
                {"stage_name": "intent_classify", "step_order": 1, "duration_ms": 0, "step_metadata": {"intent": "out_of_scope"}},
                {"stage_name": "response_save", "step_order": 2, "duration_ms": 0},
            ])
            await self._finish_execution(exec_session.id, request, execution_steps, execution_session_status, 0)
            return self._save_cache_result(
                message,
                {
                    "answer": refusal,
                    "sources": [],
                    "intent": "out_of_scope",
                    "model": None,
                    "latency_ms": 0,
                    "session_id": session_id,
                    "error": None,
                },
                cache_key,
                effective_cache_ttl,
            )

        target_course_id = mentioned_course_id or explicit_course_id or default_course_id

        # Align canonical chat session with the resolved target course.
        if target_course_id != chat_session.course_id:
            chat_session = await self.logger.create_or_update_chat_session(
                session_id=session_id,
                course_id=target_course_id,
            )

        # Determine if we need LMS data and/or RAG context from config.
        source_map = self._ocfg.get("intent_source_map", {})
        intent_sources = source_map.get(intent, {})
        need_lms = bool(intent_sources.get("lms", intent in ("organizational", "mixed", "progress", "deadline")))
        need_rag = bool(intent_sources.get("rag", intent in ("study", "mixed")))
        # Study questions should not hard-filter by course_id in RAG so that
        # generic KB materials can be used. Organizational/mixed questions
        # keep the stricter filter because they combine LMS structure with KB.
        strict_course_rag = bool(intent_sources.get("strict_course", intent != "study"))

        # Update canonical session mode based on the selected source route.
        mode = self._execution_mode_from_sources(need_lms, need_rag)
        if mode != chat_session.mode:
            chat_session = await self.logger.create_or_update_chat_session(
                session_id=session_id,
                mode=mode,
            )

        lms_data: Optional[Dict[str, Any]] = None
        lms_calls: List[Dict[str, Any]] = []
        rag_context: List[Dict[str, Any]] = []
        raw_rag_context: Optional[List[Dict[str, Any]]] = None
        rag_filters: Dict[str, Any] = {}

        async def _fetch_lms_data(course_id: int, student_user_id: int) -> Dict[str, Any]:
            """Fetch deadlines, progress and contents from LMS in parallel."""
            t_lms = time.perf_counter()
            deadlines_task = lms_adapter.get_course_deadlines(course_id)
            progress_task = lms_adapter.get_user_course_progress(course_id, user_id=student_user_id)
            contents_task = lms_adapter.get_course_contents(course_id)
            deadlines, progress, contents = await asyncio.gather(
                deadlines_task, progress_task, contents_task, return_exceptions=True
            )
            t_total = round((time.perf_counter() - t_lms) * 1000, 2)
            # Normalize exceptions into empty results + error log entries.
            result: Dict[str, Any] = {"deadlines": [], "progress": {}, "contents": [], "errors": []}
            for label, value in [("deadlines", deadlines), ("progress", progress), ("contents", contents)]:
                if isinstance(value, Exception):
                    result["errors"].append({"type": label, "error": str(value)})
                elif label == "deadlines":
                    result["deadlines"] = self._format_deadlines(value)
                elif label == "progress":
                    result["progress"] = self._format_progress(value)
                elif label == "contents":
                    result["contents"] = self._format_course_contents(value)
            return {
                "data": result,
                "has_errors": bool(result["errors"]),
                "calls": [
                    {"type": "deadlines", "course_id": course_id, "latency_ms": t_total},
                    {"type": "progress", "course_id": course_id, "user_id": student_user_id, "latency_ms": t_total},
                    {"type": "contents", "course_id": course_id, "module_count": len(result.get("contents", [])), "latency_ms": t_total},
                ],
            }

        async def _fetch_rag_context(
            query: str,
            course_id: int,
            k: int,
            threshold: float,
            strict_course: bool = True,
        ) -> Dict[str, Any]:
            """Search RAG and deduplicate chunks by content hash.

            For study questions we relax the course_id filter so generic KB
            materials (e.g. prompt-engineering FAQ, Claude Code glossary) can
            be retrieved even if they are not tagged with the current course.
            Course-matching chunks are boosted at ranking stage.
            """
            t_rag = time.perf_counter()
            try:
                rag = RagPipeline()
                results, search_timings = await rag.search(
                    query=query,
                    k=k,
                    course_id=course_id,
                    strict_course=strict_course,
                    course_boost_enabled=retrieval_tuning.course_boost_enabled,
                    course_boost_factor=retrieval_tuning.course_boost_factor,
                    embedding_timeout_ms=retrieval_tuning.embedding_timeout_ms,
                    retrieval_timeout_ms=retrieval_tuning.retrieval_timeout_ms,
                )
                t_post_start = time.perf_counter()
                seen_hashes = set()
                output: List[Dict[str, Any]] = []
                for r in results:
                    if r.distance is not None and r.distance > threshold:
                        continue
                    content_hash = hash((r.content.strip(), r.metadata.get("document_id"), r.metadata.get("chunk_index")))
                    if content_hash in seen_hashes:
                        continue
                    seen_hashes.add(content_hash)
                    output.append({
                        "content": r.content,
                        "metadata": r.metadata,
                        "distance": r.distance,
                    })
                t_post = round((time.perf_counter() - t_post_start) * 1000, 2)
                t_total = round((time.perf_counter() - t_rag) * 1000, 2)
                return {
                    "chunks": output,
                    "timings": {
                        "rag_embedding_ms": search_timings["embedding_ms"],
                        "rag_chroma_ms": search_timings["chroma_ms"],
                        "rag_postprocess_ms": t_post,
                        "rag_search_ms": t_total,
                    },
                }
            except Exception as exc:
                return {
                    "chunks": [],
                    "error": str(exc),
                    "timings": {
                        "rag_embedding_ms": 0,
                        "rag_chroma_ms": 0,
                        "rag_postprocess_ms": 0,
                        "rag_search_ms": round((time.perf_counter() - t_rag) * 1000, 2),
                    },
                }

        # Pick retrieval size: smaller for chat to reduce prompt size and latency.
        rag_k = 3 if intent in ("study", "mixed") else retrieval_tuning.top_k

        # Gather LMS and RAG in parallel for mixed/deadline; otherwise run only needed phases.
        fetch_tasks: List[Any] = []
        if need_lms and target_course_id:
            fetch_tasks.append(_fetch_lms_data(target_course_id, user_id))
        if need_rag:
            rag_filters = {"course_id": target_course_id, "strict_course": strict_course_rag}
            fetch_tasks.append(_fetch_rag_context(
                query=message,
                course_id=target_course_id,
                k=rag_k,
                threshold=retrieval_tuning.rag_distance_threshold,
                strict_course=strict_course_rag,
            ))
        if fetch_tasks:
            gathered = await asyncio.gather(*fetch_tasks, return_exceptions=True)
            rag_search_error = None
            for item in gathered:
                if isinstance(item, Exception):
                    lms_calls.append({"type": "fetch_error", "error": str(item)})
                    continue
                if "data" in item:
                    lms_data = item["data"]
                    lms_calls = item["calls"]
                    for call in lms_calls:
                        timings[f"lms_{call['type']}_ms"] = call["latency_ms"]
                if "chunks" in item:
                    rag_context = item["chunks"]
                    raw_rag_context = rag_context
                    timings.update(item["timings"])
                    if item.get("error"):
                        rag_search_error = item["error"]

            lms_fetch_errors = [c for c in lms_calls if "error" in c]
            lms_fetch_status = "error" if any(
                c.get("type") == "fetch_error" for c in lms_fetch_errors
            ) else ("warning" if lms_fetch_errors else "ok")
            rag_search_status = "error" if rag_search_error else "ok"

            if lms_fetch_status == "error" or rag_search_status == "error":
                execution_session_status = "error"
            elif lms_fetch_status == "warning" or rag_search_status == "warning":
                execution_session_status = "warning"

            if need_lms:
                lms_total_ms = round(
                    max(
                        timings.get("lms_deadlines_ms", 0),
                        timings.get("lms_progress_ms", 0),
                        timings.get("lms_contents_ms", 0),
                    ),
                    2,
                )
                execution_steps.append({
                    "stage_name": "lms_fetch",
                    "step_order": 2,
                    "status": lms_fetch_status,
                    "duration_ms": lms_total_ms,
                    "step_metadata": {
                        "has_data": bool(lms_data),
                        "errors": lms_fetch_errors,
                    },
                })
            if need_rag:
                execution_steps.append({
                    "stage_name": "rag_search",
                    "step_order": 3 if not need_lms else 3,
                    "status": rag_search_status,
                    "duration_ms": timings.get("rag_search_ms", 0),
                    "step_metadata": {
                        "chunks_count": len(rag_context),
                        "rag_filters": rag_filters,
                        "error": rag_search_error,
                    },
                })

        if lms_data:
            lms_errors = lms_data.pop("errors", [])
            for err in lms_errors:
                lms_calls.append({"type": f"lms_error_{err['type']}", "error": err["error"]})

            # Short-circuit for deadline questions: answer deterministically from LMS data.
            if intent == "deadline":
                deadline_answer, deadline_sources = self._build_deadline_answer(
                    message, lms_data, target_course_id,
                    max_lms_deadlines=self._ocfg.get("max_lms_deadlines", 5),
                )
                total_lms_ms = round(
                    timings.get("lms_deadlines_ms", 0)
                    + timings.get("lms_progress_ms", 0)
                    + timings.get("lms_contents_ms", 0),
                    2,
                )
                request = await self.logger.create_chat_request(
                    session_id=session_id,
                    chat_session_id=chat_session.id,
                    role=role,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    message=message,
                    intent=intent,
                    lms_calls=lms_calls,
                    rag_filters=rag_filters,
                )
                await self.logger.create_chat_log(
                    request_id=request.id,
                    answer=deadline_answer,
                    sources=deadline_sources,
                    llm_model=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=total_lms_ms,
                    error=None,
                )
                await self.logger.log_analytics_event(
                    event_type="chat_answer",
                    session_id=session_id,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    intent=intent,
                    payload={
                        "has_lms_data": True,
                        "rag_chunks": 0,
                        "llm_status": "short_circuit",
                        "validated": True,
                        "timings_ms": timings,
                    },
                )
                execution_steps.extend([
                    {"stage_name": "context_build", "step_order": 4, "duration_ms": 0},
                    {"stage_name": "response_save", "step_order": 8, "duration_ms": 0},
                ])
                await self._finish_execution(
                    exec_session.id,
                    request,
                    execution_steps,
                    execution_session_status,
                    total_lms_ms,
                    execution_metadata={"timings_ms": timings, "short_circuit": True, "route": "lms"},
                )
                return self._save_cache_result(
                    message,
                    {
                        "answer": deadline_answer,
                        "sources": deadline_sources,
                        "intent": intent,
                        "model": None,
                        "latency_ms": total_lms_ms,
                        "session_id": session_id,
                        "error": None,
                    },
                    cache_key,
                    effective_cache_ttl,
                )

            # Short-circuit for progress questions: answer deterministically from LMS data.
            if intent == "progress":
                progress_answer, progress_sources = self._build_progress_answer(
                    message, lms_data, target_course_id,
                    max_lms_contents=self._ocfg.get("max_lms_contents", 12),
                    fallback_messages=self._ocfg.get("fallback_messages", {}),
                )
                total_lms_ms = round(
                    timings.get("lms_deadlines_ms", 0)
                    + timings.get("lms_progress_ms", 0)
                    + timings.get("lms_contents_ms", 0),
                    2,
                )
                request = await self.logger.create_chat_request(
                    session_id=session_id,
                    chat_session_id=chat_session.id,
                    role=role,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    message=message,
                    intent=intent,
                    lms_calls=lms_calls,
                    rag_filters=rag_filters,
                )
                await self.logger.create_chat_log(
                    request_id=request.id,
                    answer=progress_answer,
                    sources=progress_sources,
                    llm_model=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=total_lms_ms,
                    error=None,
                )
                await self.logger.log_analytics_event(
                    event_type="chat_answer",
                    session_id=session_id,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    intent=intent,
                    payload={
                        "has_lms_data": True,
                        "rag_chunks": 0,
                        "llm_status": "short_circuit",
                        "validated": True,
                        "timings_ms": timings,
                    },
                )
                execution_steps.extend([
                    {"stage_name": "context_build", "step_order": 4, "duration_ms": 0},
                    {"stage_name": "response_save", "step_order": 8, "duration_ms": 0},
                ])
                await self._finish_execution(
                    exec_session.id,
                    request,
                    execution_steps,
                    execution_session_status,
                    total_lms_ms,
                    execution_metadata={"timings_ms": timings, "short_circuit": True, "route": "lms"},
                )
                return self._save_cache_result(
                    message,
                    {
                        "answer": progress_answer,
                        "sources": progress_sources,
                        "intent": intent,
                        "model": None,
                        "latency_ms": total_lms_ms,
                        "session_id": session_id,
                        "error": None,
                    },
                    cache_key,
                    effective_cache_ttl,
                )

            # Short-circuit for count questions: answer deterministically from LMS data.
            message_lower = message.lower()
            is_count_question = any(kw in message_lower for kw in ("сколько", "количество", "всего"))
            asks_assignments_or_modules = any(
                kw in message_lower
                for kw in ("задание", "задания", "дз", "модуль", "модули", "урок", "уроки", "курс")
            )
            if intent == "organizational" and is_count_question and asks_assignments_or_modules:
                count_answer, count_sources = self._build_organizational_count_answer(
                    message, lms_data, target_course_id
                )
                total_lms_ms = round(
                    timings.get("lms_deadlines_ms", 0)
                    + timings.get("lms_progress_ms", 0)
                    + timings.get("lms_contents_ms", 0),
                    2,
                )
                request = await self.logger.create_chat_request(
                    session_id=session_id,
                    chat_session_id=chat_session.id,
                    role=role,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    message=message,
                    intent=intent,
                    lms_calls=lms_calls,
                    rag_filters=rag_filters,
                )
                await self.logger.create_chat_log(
                    request_id=request.id,
                    answer=count_answer,
                    sources=count_sources,
                    llm_model=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=total_lms_ms,
                    error=None,
                )
                await self.logger.log_analytics_event(
                    event_type="chat_answer",
                    session_id=session_id,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    intent=intent,
                    payload={
                        "has_lms_data": True,
                        "rag_chunks": 0,
                        "llm_status": "short_circuit",
                        "validated": True,
                        "timings_ms": timings,
                    },
                )
                execution_steps.extend([
                    {"stage_name": "context_build", "step_order": 4, "duration_ms": 0},
                    {"stage_name": "response_save", "step_order": 8, "duration_ms": 0},
                ])
                await self._finish_execution(
                    exec_session.id,
                    request,
                    execution_steps,
                    execution_session_status,
                    total_lms_ms,
                    execution_metadata={"timings_ms": timings, "short_circuit": True, "route": "lms"},
                )
                return self._save_cache_result(
                    message,
                    {
                        "answer": count_answer,
                        "sources": count_sources,
                        "intent": intent,
                        "model": None,
                        "latency_ms": total_lms_ms,
                        "session_id": session_id,
                        "error": None,
                    },
                    cache_key,
                    effective_cache_ttl,
                )

            # Short-circuit: if the user asks about deadlines/assignments and there are none.
            deadlines = lms_data.get("deadlines", [])
            if (
                ("дедлайн" in message_lower
                 or "задание" in message_lower
                 or "срок" in message_lower)
                and not deadlines
            ):
                no_lms_data_template = self._ocfg.get(
                    "fallback_messages", {}
                ).get(
                    "no_lms_data",
                    "В курсе пока нет опубликованных заданий с дедлайнами. Если вы ожидаете увидеть задание, обратитесь к преподавателю."
                )
                no_deadline_answer = no_lms_data_template
                total_lms_ms = round(
                    timings.get("lms_deadlines_ms", 0)
                    + timings.get("lms_progress_ms", 0)
                    + timings.get("lms_contents_ms", 0),
                    2,
                )
                request = await self.logger.create_chat_request(
                    session_id=session_id,
                    role=role,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    message=message,
                    intent=intent,
                    lms_calls=lms_calls,
                    rag_filters=rag_filters,
                )
                await self.logger.create_chat_log(
                    request_id=request.id,
                    answer=no_deadline_answer,
                    sources=[],
                    llm_model=None,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=total_lms_ms,
                    error=None,
                )
                await self.logger.log_analytics_event(
                    event_type="chat_answer",
                    session_id=session_id,
                    course_id=target_course_id,
                    difficulty=difficulty,
                    intent=intent,
                    payload={
                        "has_lms_data": bool(lms_data),
                        "rag_chunks": 0,
                        "llm_status": "short_circuit",
                        "validated": True,
                        "timings_ms": timings,
                    },
                )
                execution_steps.extend([
                    {"stage_name": "context_build", "step_order": 4, "duration_ms": 0},
                    {"stage_name": "response_save", "step_order": 8, "duration_ms": 0},
                ])
                await self._finish_execution(
                    exec_session.id,
                    request,
                    execution_steps,
                    execution_session_status,
                    total_lms_ms,
                    execution_metadata={"timings_ms": timings, "short_circuit": True, "route": "lms"},
                )
                return self._save_cache_result(
                    message,
                    {
                        "answer": no_deadline_answer,
                        "sources": [],
                        "intent": intent,
                        "model": None,
                        "latency_ms": total_lms_ms,
                        "session_id": session_id,
                        "error": None,
                    },
                    cache_key,
                    effective_cache_ttl,
                )

        # Short-circuit: deadline questions with disabled LMS must not fall back
        # to a generic LLM call because the model would hallucinate deadlines
        # from chat history or from generic KB chunks. Use the configured
        # fallback message instead. RAG context is intentionally ignored here:
        # deadlines are authoritative LMS data.
        if intent == "deadline" and not need_lms:
            no_lms_template = self._ocfg.get(
                "fallback_messages", {}
            ).get(
                "no_lms_data",
                "В курсе пока нет опубликованных заданий с дедлайнами. Обратитесь к преподавателю."
            )
            short_latency = round(
                timings.get("lms_deadlines_ms", 0)
                + timings.get("lms_progress_ms", 0)
                + timings.get("lms_contents_ms", 0)
                + timings.get("rag_search_ms", 0),
                2,
            )
            request = await self.logger.create_chat_request(
                session_id=session_id,
                chat_session_id=chat_session.id,
                role=role,
                course_id=target_course_id,
                difficulty=difficulty,
                message=message,
                intent=intent,
                lms_calls=lms_calls,
                rag_filters=rag_filters,
            )
            await self.logger.create_chat_log(
                request_id=request.id,
                answer=no_lms_template,
                sources=[],
                llm_model=None,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=short_latency,
                error=None,
            )
            await self.logger.log_analytics_event(
                event_type="chat_answer",
                session_id=session_id,
                course_id=target_course_id,
                difficulty=difficulty,
                intent=intent,
                payload={
                    "has_lms_data": False,
                    "rag_chunks": 0,
                    "llm_status": "short_circuit",
                    "validated": True,
                    "timings_ms": timings,
                },
            )
            execution_steps.extend([
                {"stage_name": "context_build", "step_order": 4, "duration_ms": 0},
                {"stage_name": "response_save", "step_order": 8, "duration_ms": 0},
            ])
            await self._finish_execution(
                exec_session.id,
                request,
                execution_steps,
                execution_session_status,
                short_latency,
                execution_metadata={"timings_ms": timings, "short_circuit": True, "route": "fallback_no_lms"},
            )
            return self._save_cache_result(
                message,
                {
                    "answer": no_lms_template,
                    "sources": [],
                    "intent": intent,
                    "model": None,
                    "latency_ms": short_latency,
                    "session_id": session_id,
                    "error": None,
                },
                cache_key,
                effective_cache_ttl,
            )

        # Short-circuit: if this is a pure study question and no relevant context
        # was found, refuse immediately without calling the LLM.
        if intent == "study" and not rag_context and not lms_data:
            no_rag_template = self._ocfg.get(
                "fallback_messages", {}
            ).get(
                "no_rag_context",
                "У меня недостаточно данных, чтобы точно ответить. Обратитесь к преподавателю."
            )
            refusal = no_rag_template
            short_latency = round(
                timings.get("lms_deadlines_ms", 0)
                + timings.get("lms_progress_ms", 0)
                + timings.get("lms_contents_ms", 0)
                + timings.get("rag_search_ms", 0),
                2,
            )
            request = await self.logger.create_chat_request(
                session_id=session_id,
                chat_session_id=chat_session.id,
                role=role,
                course_id=target_course_id,
                difficulty=difficulty,
                message=message,
                intent="out_of_scope",
                lms_calls=lms_calls,
                rag_filters=rag_filters,
            )
            await self.logger.create_chat_log(
                request_id=request.id,
                answer=refusal,
                sources=[],
                llm_model=None,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                latency_ms=short_latency,
                error=None,
            )
            await self.logger.log_analytics_event(
                event_type="chat_answer",
                session_id=session_id,
                course_id=target_course_id,
                difficulty=difficulty,
                intent="out_of_scope",
                payload={
                    "has_lms_data": bool(lms_data),
                    "rag_chunks": 0,
                    "llm_status": "short_circuit",
                    "validated": True,
                    "timings_ms": timings,
                },
            )
            execution_steps.extend([
                {"stage_name": "context_build", "step_order": 4, "duration_ms": 0},
                {"stage_name": "response_save", "step_order": 8, "duration_ms": 0},
            ])
            await self._finish_execution(
                exec_session.id,
                request,
                execution_steps,
                execution_session_status,
                short_latency,
                execution_metadata={"timings_ms": timings, "short_circuit": True, "route": "rag" if need_rag else "text"},
            )
            return self._save_cache_result(
                message,
                {
                    "answer": refusal,
                    "sources": [],
                    "intent": "out_of_scope",
                    "model": None,
                    "latency_ms": short_latency,
                    "session_id": session_id,
                    "error": None,
                },
                cache_key,
                effective_cache_ttl,
            )

        # Persist request
        request = await self.logger.create_chat_request(
            session_id=session_id,
            chat_session_id=chat_session.id,
            role=role,
            course_id=target_course_id,
            difficulty=difficulty,
            message=message,
            intent=intent,
            lms_calls=lms_calls,
            rag_filters=rag_filters,
        )
        execution_steps.append({
            "stage_name": "context_build",
            "step_order": 4,
            "duration_ms": 0,
            "step_metadata": {
                "has_lms_data": bool(lms_data),
                "rag_chunks": len(rag_context),
                "rag_filters": rag_filters,
                "rag_distance_threshold": retrieval_tuning.rag_distance_threshold,
                "rag_context": [
                    {
                        "content": chunk.get("content"),
                        "distance": chunk.get("distance"),
                        "metadata": chunk.get("metadata"),
                    }
                    for chunk in (raw_rag_context if raw_rag_context is not None else rag_context)
                ],
            },
        })

        # Build prompt and call LLM
        prompt_builder = PromptBuilder(config, orchestrator_config=ocfg)
        prompt = prompt_builder.build(
            message=message,
            role=role,
            difficulty=difficulty,
            course_id=target_course_id,
            lms_data=lms_data,
            rag_context=rag_context,
            history=history,
        )

        # Choose output token budget by intent/difficulty from config.
        # The actual limit is clamped to the active config's max_tokens in LLMAdapter.
        token_budgets = self._ocfg.get("intent_max_tokens", {})
        if intent == "organizational":
            llm_max_tokens = token_budgets.get("organizational", 500)
        elif intent == "study" and difficulty and difficulty.lower() in (
            "beginner", "начинающий", "базовый"
        ):
            llm_max_tokens = token_budgets.get("study_beginner", 650)
        elif intent == "mixed":
            llm_max_tokens = token_budgets.get("mixed", 800)
        else:
            # Advanced study and any other intent: cap below the config default
            # to keep latency under the NFR ceiling.
            llm_max_tokens = token_budgets.get("default", 750)

        llm = LLMAdapter(config)
        llm_result: LlmResponse = await llm.generate(prompt, max_tokens=llm_max_tokens)
        timings["llm_generate_ms"] = llm_result.latency_ms or 0
        execution_steps.append({
            "stage_name": "llm_call",
            "step_order": 5,
            "duration_ms": llm_result.latency_ms,
            "status": "ok" if not llm_result.error else "error",
            "step_metadata": {
                "model": llm_result.model,
                "prompt_tokens": llm_result.prompt_tokens,
                "completion_tokens": llm_result.completion_tokens,
                "total_tokens": llm_result.total_tokens,
                "error": llm_result.error,
            },
        })

        # Detect truncated responses so methodologists can see when max_tokens is too tight.
        llm_truncated = bool(llm_result.error and "truncated" in llm_result.error)
        await self.logger.create_llm_call(
            request_id=request.id,
            model=llm_result.model,
            prompt=prompt,
            response=llm_result.content,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            total_tokens=llm_result.total_tokens,
            latency_ms=llm_result.latency_ms,
            status="ok" if not llm_result.error else "error",
            error=llm_result.error,
        )

        # Build sources only from materials actually referenced in the answer.
        # This is a code-level responsibility: the prompt can ask, but only code
        # can reliably enforce the link between the answer text and the source list.
        sources: List[Dict[str, Any]] = []
        answer_lower = (llm_result.content or "").lower()

        def _is_referenced(title: str) -> bool:
            """Return True if the source title is clearly referenced in the answer."""
            if not title:
                return False
            title_lower = title.lower()
            # Direct substring match is enough for most source titles.
            if title_lower in answer_lower:
                return True
            # Also match without the "ДЗ:" prefix for assignments.
            clean = re.sub(r"^(дз|задание|assignment)[:\s]+", "", title_lower)
            if clean and clean in answer_lower:
                return True
            return False

        if lms_data:
            seen_lms_titles = set()
            for item in lms_data.get("contents", []):
                title = item.get("name")
                if title and _is_referenced(title):
                    key = (title, item.get("url"))
                    if key not in seen_lms_titles:
                        seen_lms_titles.add(key)
                        sources.append({
                            "type": "lms",
                            "title": title,
                            "url": item.get("url"),
                            "module": item.get("section_name"),
                        })
            for d in lms_data.get("deadlines", []):
                title = d.get("name")
                if title and _is_referenced(title):
                    key = (title, d.get("url"))
                    if key not in seen_lms_titles:
                        seen_lms_titles.add(key)
                        sources.append({
                            "type": "lms",
                            "title": title,
                            "url": d.get("url"),
                        })

        # KB sources: keep unique documents returned by RAG that are semantically relevant.
        # We intentionally do NOT require the LLM to verbatim-cite the document title:
        # educational answers often paraphrase concepts without repeating the KB title.
        # Deduplication and non-empty context are enough to attribute the answer.
        rag_distance_threshold = retrieval_tuning.rag_distance_threshold
        seen_kb_ids = set()
        for chunk in rag_context:
            distance = chunk.get("distance")
            if distance is not None and distance > rag_distance_threshold:
                continue
            meta = chunk.get("metadata", {})
            doc_id = meta.get("document_id")
            if doc_id in seen_kb_ids:
                continue
            seen_kb_ids.add(doc_id)
            title = meta.get("title") or f"Материал Knowledge Base (документ {doc_id})"
            sources.append({
                "type": "kb",
                "title": title,
                "document_id": doc_id,
                "chunk_index": meta.get("chunk_index"),
            })
        execution_steps.append({
            "stage_name": "source_attach",
            "step_order": 6,
            "duration_ms": 0,
            "step_metadata": {
                "lms_sources": len([s for s in sources if s.get("type") == "lms"]),
                "kb_sources": len([s for s in sources if s.get("type") == "kb"]),
            },
        })

        # Validate answer
        t_validation = time.perf_counter()
        validator = AnswerValidator(
            answer=llm_result.content,
            sources=sources,
            has_lms_or_rag_context=bool(lms_data or rag_context),
            user_message=message,
        )
        validation = validator.validate()
        timings["validation_ms"] = round((time.perf_counter() - t_validation) * 1000, 2)
        execution_steps.append({
            "stage_name": "answer_validate",
            "step_order": 7,
            "duration_ms": timings["validation_ms"],
            "status": "ok" if validation.is_valid else "warning",
            "step_metadata": {
                "is_valid": validation.is_valid,
                "fallback": validation.fallback,
                "refusal": validation.refusal,
                "issues": validation.issues,
            },
        })

        final_answer = validation.answer if validation.is_valid else validation.answer
        # Do not show sources when the answer is a fallback/refusal/out-of-scope.
        final_sources = sources if validation.is_valid and not validation.fallback and not validation.refusal else []

        total_latency = round(
            timings.get("intent_detect_ms", 0)
            + max(timings.get("lms_deadlines_ms", 0), timings.get("lms_progress_ms", 0), timings.get("lms_contents_ms", 0))
            + timings.get("rag_search_ms", 0)
            + (llm_result.latency_ms or 0)
            + timings.get("validation_ms", 0),
            2,
        )

        await self.logger.create_chat_log(
            request_id=request.id,
            answer=final_answer,
            sources=final_sources,
            llm_model=llm_result.model,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            total_tokens=llm_result.total_tokens,
            latency_ms=total_latency,
            error=llm_result.error or ("; ".join(validation.issues) if validation.issues else None),
            cache_hit=False,
        )
        execution_steps.append({
            "stage_name": "response_save",
            "step_order": 8,
            "duration_ms": 0,
            "step_metadata": {
                "has_answer": bool(final_answer),
                "sources_count": len(final_sources),
            },
        })

        await self.logger.log_analytics_event(
            event_type="chat_answer",
            session_id=session_id,
            course_id=target_course_id,
            difficulty=difficulty,
            intent=intent,
            payload={
                "has_lms_data": bool(lms_data),
                "rag_chunks": len(rag_context),
                "llm_status": "ok" if not llm_result.error else "error",
                "llm_truncated": llm_truncated,
                "validated": validation.is_valid,
                "timings_ms": timings,
            },
        )

        if llm_result.error:
            execution_session_status = "error"
        await self._finish_execution(
            exec_session.id,
            request,
            execution_steps,
            execution_session_status,
            total_latency,
            execution_metadata={"timings_ms": timings, "route": mode},
        )

        return self._save_cache_result(
            message,
            {
                "answer": final_answer,
                "sources": final_sources,
                "intent": intent,
                "model": llm_result.model,
                "latency_ms": total_latency,
                "session_id": session_id,
                "error": llm_result.error,
            },
            cache_key,
            effective_cache_ttl,
        )
