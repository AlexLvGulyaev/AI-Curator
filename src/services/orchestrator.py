"""Orchestrator for AI Curator chat: classify, gather context, generate answer."""

import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from adapters.lms_adapter import lms_adapter
from services.ai_config import AiConfigService
from services.answer_validator import AnswerValidator
from services.llm_adapter import LLMAdapter, LlmResponse
from services.logger import LoggerService
from services.prompt_builder import PromptBuilder
from services.rag_pipeline import RagPipeline


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

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = LoggerService(db)
        self.ai_config_service = AiConfigService(db)

    # Common Russian sentence starters that are NOT course names.
    _NON_COURSE_STARTERS = {
        "когда", "сколько", "какой", "какая", "какое", "какие", "как", "что",
        "почему", "зачем", "где", "куда", "откуда", "кто", "чей", "чьё", "чьи",
        "объясни", "расскажи", "покажи", "скажи", "дай", "перечисли", "укажи",
        "выведи", "напиши", "сделай", "поставь", "выставь", "перенеси", "сообщи",
        "пройди", "прочитай", "повтори", "изучи", "опиши", "привет", "спасибо",
    }

    @staticmethod
    def _extract_course_mentions(message: str) -> List[str]:
        """Extract potential course names from the user message.

        Conservative heuristics:
        - quoted strings only when they are preceded by a course marker ("курс");
        - explicit "курс X" / "по курсу X" patterns;
        - short capitalized phrases after "курс Name".

        Assignment and module names quoted in questions like
        "Что повторить перед заданием \"Ролевые промпты\"" are intentionally
        excluded so they do not trigger a "course not found" refusal.
        """
        mentions = []

        # Quoted strings are course names only if preceded by a course marker.
        for match in re.finditer(
            r'курс[аеуом]?\s+["«"]([^"""]+)["""]',
            message,
            re.IGNORECASE,
        ):
            mentions.append(match.group(1).strip())

        # Capture "по курсу Name" / "курс Name" where Name is a short proper noun.
        # This is much more reliable than scanning the whole sentence.
        for match in re.finditer(
            r'(?:по\s+)?курс[аеуом]?\s+([А-ЯA-Z][а-яa-zА-ЯA-Z0-9\-]*(?:\s+[а-яa-zА-ЯA-Z0-9\-]+){0,2})',
            message,
            re.IGNORECASE,
        ):
            candidate = match.group(1).strip()
            words = candidate.split()
            if len(words) >= 1:
                mentions.append(candidate)
        return mentions

    @staticmethod
    def _resolve_role_context(role: Optional[str]) -> Dict[str, Any]:
        """Return demo user_id and available course_ids for a role."""
        if role and role in Orchestrator.ROLE_CONFIG:
            return Orchestrator.ROLE_CONFIG[role]
        # Fallback to legacy student_demo if role is missing/unknown.
        return Orchestrator.ROLE_CONFIG["student_demo"]

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
    ) -> Optional[int]:
        """Return course_id if the message clearly mentions one of available courses."""
        if not available_courses:
            return None
        mentions = Orchestrator._extract_course_mentions(message)
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
    ) -> Optional[str]:
        """Return the mentioned course name if it is not in available courses."""
        if not available_courses:
            return None
        mentions = Orchestrator._extract_course_mentions(message)
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
    def detect_intent(message: str) -> str:
        """Classify message intent."""
        lower = message.lower()
        is_progress = any(kw in lower for kw in Orchestrator.PROGRESS_KEYWORDS)
        is_org = any(kw in lower for kw in Orchestrator.ORG_KEYWORDS)
        is_study = any(kw in lower for kw in Orchestrator.STUDY_KEYWORDS)
        # Progress questions often overlap with organizational keywords (module/assignment).
        # Treat them as a dedicated intent so we can answer from LMS progress directly.
        if is_progress:
            return "progress"
        if is_org and is_study:
            return "mixed"
        if is_org:
            return "organizational"
        if is_study:
            return "study"
        # Default to study to leverage RAG for general course questions.
        return "study"

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
    def _build_progress_answer(
        message: str,
        lms_data: Dict[str, Any],
        course_id: int,
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Build a deterministic answer for progress-related questions."""
        progress = lms_data.get("progress", {}) or {}
        contents = lms_data.get("contents", []) or []
        completion_status = progress.get("completion_status", "in_progress")

        # Collect unique module names from course contents (section names).
        # Skip generic section 0 names that duplicate module names (e.g. "Основы"
        # vs "Модуль 1. Основы").
        raw_sections: List[str] = []
        seen_sections: set = set()
        for item in contents:
            section = (item.get("section_name") or "").strip()
            if not section or section in seen_sections:
                continue
            seen_sections.add(section)
            raw_sections.append(section)

        # Drop sections that are substrings of a more specific module section.
        modules: List[str] = []
        lower_all = [s.lower() for s in raw_sections]
        for section in raw_sections:
            lower = section.lower()
            if lower in ("общее", "general"):
                continue
            if any(other != lower and lower in other for other in lower_all):
                continue
            modules.append(section)

        # Grade items for assignments.
        grade_items = progress.get("grade_items", []) or []
        assignments = [gi for gi in grade_items if gi.get("item_module") == "assign"]
        graded = [gi for gi in assignments if gi.get("grade_raw") is not None]

        # Overall grade summary.
        grade = progress.get("overall_grade_formatted")
        grade_line = f" Общая оценка: {grade}." if grade and grade != "-" else ""

        lower_message = message.lower()
        asks_modules = any(kw in lower_message for kw in ("модуль", "модули", "прошёл", "прошел", "завершил"))
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

        # List modules when asked.
        if asks_modules and modules:
            body += "\n\nМодули курса:\n" + "\n".join(f"- {m}" for m in modules[:20])

        # List graded assignments explicitly when asked, if not already shown.
        if asks_assignments and not graded:
            if assignments:
                body += "\n\nСданные задания:\n" + "\n".join(
                    f"- {gi.get('name', 'Задание')}: {gi.get('grade_formatted') or gi.get('gradeformatted', '-')}" for gi in assignments
                )
            else:
                body += "\n\nПока нет сданных заданий с выставленной оценкой."

        # Build sources: only unique course modules referenced in the answer.
        # Use the deduplicated `modules` list so generic section 0 names are excluded.
        sources: List[Dict[str, Any]] = []
        seen_source_sections: set = set()
        # Pick a representative URL for each module from the first matching content item.
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

    async def process(
        self,
        message: str,
        *,
        role: Optional[str] = None,
        difficulty: Optional[str] = None,
        course_id: Optional[int] = None,
        session_id: Optional[str] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Process a student message end-to-end and return answer + sources."""
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Resolve demo user context from role.
        role_context = self._resolve_role_context(role)
        user_id = role_context["user_id"]
        available_course_ids: List[int] = role_context["course_ids"]
        default_course_id: int = role_context["default_course_id"]

        # Determine target course: mentioned course in message takes precedence over
        # explicit UI selection, then default, but only if the mentioned course is
        # actually available to this role. Otherwise we refuse.
        available_courses = await self._get_available_courses(available_course_ids)
        mentioned_course_id = self._find_mentioned_course(message, available_courses)
        explicit_course_id = course_id if course_id in available_course_ids else None

        # Check whether the user is asking about a course they are not enrolled in.
        other_course = self._looks_like_other_course(message, available_courses)
        if other_course:
            refusal = (
                f"У меня нет данных о курсе «{other_course}» для вашей учётной записи. "
                "Обратитесь к преподавателю, если вопрос касается другого курса."
            )
            request = await self.logger.create_chat_request(
                session_id=session_id,
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
            return {
                "answer": refusal,
                "sources": [],
                "intent": "out_of_scope",
                "model": None,
                "latency_ms": 0,
                "session_id": session_id,
                "error": None,
            }

        target_course_id = mentioned_course_id or explicit_course_id or default_course_id

        # Early short-circuit for requests that must be refused (grades, deadlines).
        # This avoids wasting tokens and latency on LLM/RAG/LMS calls.
        refusal_topic = AnswerValidator.requires_refusal(message)
        if refusal_topic:
            refusal = (
                "Я не выставляю оценки и не изменяю учебный процесс. "
                "Обратитесь к преподавателю."
            )
            request = await self.logger.create_chat_request(
                session_id=session_id,
                role=role,
                course_id=target_course_id,
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
            return {
                "answer": refusal,
                "sources": [],
                "intent": "refusal",
                "model": None,
                "latency_ms": 0,
                "session_id": session_id,
                "error": None,
            }

        intent = self.detect_intent(message)

        # Determine if we need LMS data and/or RAG context.
        need_lms = intent in ("organizational", "mixed", "progress")
        need_rag = intent in ("study", "mixed")

        lms_data: Optional[Dict[str, Any]] = None
        lms_calls: List[Dict[str, Any]] = []
        rag_context: List[Dict[str, Any]] = []
        rag_filters: Dict[str, Any] = {}

        # Gather LMS data
        if need_lms and target_course_id:
            try:
                start = __import__("time").perf_counter()
                deadlines = await lms_adapter.get_course_deadlines(target_course_id)
                progress = await lms_adapter.get_user_course_progress(target_course_id, user_id=user_id)
                contents = await lms_adapter.get_course_contents(target_course_id)
                elapsed = round((__import__("time").perf_counter() - start) * 1000, 2)
                lms_data = {
                    "deadlines": self._format_deadlines(deadlines),
                    "progress": self._format_progress(progress),
                    "contents": self._format_course_contents(contents),
                }
                lms_calls.append({"type": "deadlines", "course_id": target_course_id, "latency_ms": elapsed})
                lms_calls.append({"type": "progress", "course_id": target_course_id, "user_id": user_id, "latency_ms": elapsed})
                lms_calls.append({"type": "contents", "course_id": target_course_id, "module_count": len(contents), "latency_ms": elapsed})

                # Short-circuit for progress questions: answer deterministically from LMS data.
                if intent == "progress":
                    progress_answer, progress_sources = self._build_progress_answer(
                        message, lms_data, target_course_id
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
                        answer=progress_answer,
                        sources=progress_sources,
                        llm_model=None,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        latency_ms=elapsed,
                        error=None,
                    )
                    return {
                        "answer": progress_answer,
                        "sources": progress_sources,
                        "intent": intent,
                        "model": None,
                        "latency_ms": elapsed,
                        "session_id": session_id,
                        "error": None,
                    }

                # Short-circuit: if the user asks about deadlines/assignments and there are none.
                if (
                    "дедлайн" in message.lower()
                    or "задание" in message.lower()
                    or "срок" in message.lower()
                ) and not deadlines:
                    no_deadline_answer = (
                        f"В курсе пока нет опубликованных заданий с дедлайнами. "
                        "Если вы ожидаете увидеть задание, обратитесь к преподавателю."
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
                        latency_ms=elapsed,
                        error=None,
                    )
                    return {
                        "answer": no_deadline_answer,
                        "sources": [],
                        "intent": intent,
                        "model": None,
                        "latency_ms": elapsed,
                        "session_id": session_id,
                        "error": None,
                    }
            except Exception as exc:
                lms_calls.append({"type": "lms_error", "error": str(exc)})

        # Gather RAG context
        if need_rag:
            try:
                rag = RagPipeline()
                config = await self.ai_config_service.get_active()
                # Difficulty is intentionally not used as a retrieval filter.
                # Per spec, difficulty adaptation is handled by the prompt/LLM,
                # while RAG returns all relevant course/context chunks.
                rag_filters = {
                    "course_id": course_id,
                }
                results = await rag.search(
                    query=message,
                    k=config.top_k_retrieval,
                    course_id=target_course_id,
                )
                # Filter to relevant chunks using a distance threshold so that
                # out-of-scope questions do not carry unrelated context to the LLM.
                # Cosine distances in this collection are typically 0.4-1.2; 1.35
                # keeps clearly irrelevant chunks out without dropping borderline
                # educational matches.
                RAG_DISTANCE_THRESHOLD = 1.35
                rag_context = [
                    {
                        "content": r.content,
                        "metadata": r.metadata,
                        "distance": r.distance,
                    }
                    for r in results
                    if r.distance is None or r.distance <= RAG_DISTANCE_THRESHOLD
                ]
            except Exception as exc:
                rag_context = []

        # Short-circuit: if this is a pure study question and no relevant context
        # was found, refuse immediately without calling the LLM.
        if intent == "study" and not rag_context and not lms_data:
            refusal = (
                "У меня недостаточно данных, чтобы точно ответить. "
                "Обратитесь к преподавателю."
            )
            request = await self.logger.create_chat_request(
                session_id=session_id,
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
                latency_ms=sum(c.get("latency_ms", 0) or 0 for c in lms_calls),
                error=None,
            )
            return {
                "answer": refusal,
                "sources": [],
                "intent": "out_of_scope",
                "model": None,
                "latency_ms": sum(c.get("latency_ms", 0) or 0 for c in lms_calls),
                "session_id": session_id,
                "error": None,
            }

        # Persist request
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

        # Build prompt and call LLM
        config = await self.ai_config_service.get_active()
        prompt_builder = PromptBuilder(config)
        prompt = prompt_builder.build(
            message=message,
            role=role,
            difficulty=difficulty,
            course_id=target_course_id,
            lms_data=lms_data,
            rag_context=rag_context,
            history=history,
        )

        llm = LLMAdapter(config)
        llm_result: LlmResponse = await llm.generate(prompt)

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
        RAG_DISTANCE_THRESHOLD = 1.35  # cosine distance; values above this are considered irrelevant
        seen_kb_ids = set()
        for chunk in rag_context:
            distance = chunk.get("distance")
            if distance is not None and distance > RAG_DISTANCE_THRESHOLD:
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

        # Validate answer
        validator = AnswerValidator(
            answer=llm_result.content,
            sources=sources,
            has_lms_or_rag_context=bool(lms_data or rag_context),
            user_message=message,
        )
        validation = validator.validate()

        final_answer = validation.answer if validation.is_valid else validation.answer
        # Do not show sources when the answer is a fallback/refusal/out-of-scope.
        final_sources = sources if validation.is_valid and not validation.fallback and not validation.refusal else []

        total_latency = round(
            sum(c.get("latency_ms", 0) or 0 for c in lms_calls) + (llm_result.latency_ms or 0), 2
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
        )

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
                "validated": validation.is_valid,
            },
        )

        return {
            "answer": final_answer,
            "sources": final_sources,
            "intent": intent,
            "model": llm_result.model,
            "latency_ms": total_latency,
            "session_id": session_id,
            "error": llm_result.error,
        }
