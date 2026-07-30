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
        "сколько осталось",
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
    ]

    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = LoggerService(db)
        self.ai_config_service = AiConfigService(db)

    @staticmethod
    def detect_intent(message: str) -> str:
        """Classify message intent."""
        lower = message.lower()
        is_org = any(kw in lower for kw in Orchestrator.ORG_KEYWORDS)
        is_study = any(kw in lower for kw in Orchestrator.STUDY_KEYWORDS)
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

        intent = self.detect_intent(message)

        # Determine if we need LMS data and/or RAG context.
        need_lms = intent in ("organizational", "mixed")
        need_rag = intent in ("study", "mixed")

        lms_data: Optional[Dict[str, Any]] = None
        lms_calls: List[Dict[str, Any]] = []
        rag_context: List[Dict[str, Any]] = []
        rag_filters: Dict[str, Any] = {}

        # Gather LMS data
        if need_lms and course_id:
            try:
                start = __import__("time").perf_counter()
                deadlines = await lms_adapter.get_course_deadlines(course_id)
                progress = await lms_adapter.get_user_course_progress(course_id, user_id=3)
                elapsed = round((__import__("time").perf_counter() - start) * 1000, 2)
                lms_data = {
                    "deadlines": self._format_deadlines(deadlines),
                    "progress": self._format_progress(progress),
                }
                lms_calls.append({"type": "deadlines", "course_id": course_id, "latency_ms": elapsed})
                lms_calls.append({"type": "progress", "course_id": course_id, "user_id": 3, "latency_ms": elapsed})
            except Exception as exc:
                lms_calls.append({"type": "lms_error", "error": str(exc)})

        # Gather RAG context
        if need_rag:
            try:
                rag = RagPipeline()
                config = await self.ai_config_service.get_active()
                rag_filters = {
                    "course_id": course_id,
                    "difficulty": difficulty,
                }
                results = await rag.search(
                    query=message,
                    k=config.top_k_retrieval,
                    course_id=course_id,
                    difficulty=difficulty,
                )
                rag_context = [
                    {
                        "content": r.content,
                        "metadata": r.metadata,
                        "distance": r.distance,
                    }
                    for r in results
                ]
            except Exception as exc:
                rag_context = []

        # Persist request
        request = await self.logger.create_chat_request(
            session_id=session_id,
            role=role,
            course_id=course_id,
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
            course_id=course_id,
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

        # Build sources
        sources: List[Dict[str, Any]] = []
        if lms_data and lms_data.get("deadlines"):
            for d in lms_data["deadlines"][:5]:
                sources.append({
                    "type": "lms",
                    "title": d.get("name", "Задание LMS"),
                    "url": d.get("url"),
                })
        for chunk in rag_context[:5]:
            meta = chunk.get("metadata", {})
            doc_id = meta.get("document_id")
            sources.append({
                "type": "kb",
                "title": f"Материал Knowledge Base (документ {doc_id})",
                "document_id": doc_id,
                "chunk_index": meta.get("chunk_index"),
            })

        # Validate answer
        validator = AnswerValidator(
            answer=llm_result.content,
            sources=sources,
            has_lms_or_rag_context=bool(lms_data or rag_context),
        )
        validation = validator.validate()

        final_answer = validation.answer if validation.is_valid else validation.answer
        final_sources = sources if validation.is_valid else []

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
            course_id=course_id,
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
