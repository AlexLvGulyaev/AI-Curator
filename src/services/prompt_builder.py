"""Prompt builder for AI Curator LLM chat."""

from typing import Any, Dict, List, Optional

from models.ai_config import AiConfig


class PromptBuilder:
    """Assemble a structured prompt for the LLM from context and rules."""

    def __init__(self, config: AiConfig):
        self.config = config

    def build(
        self,
        message: str,
        role: Optional[str] = None,
        difficulty: Optional[str] = None,
        course_id: Optional[int] = None,
        lms_data: Optional[Dict[str, Any]] = None,
        rag_context: Optional[List[Dict[str, Any]]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Return a single prompt string ready for the LLM adapter."""
        parts: List[str] = []

        # System prompt from active config
        parts.append(self.config.system_prompt.strip())

        # User context
        context_lines = []
        if role:
            context_lines.append(f"Роль студента: {role}.")
        if difficulty:
            lower = difficulty.lower()
            if lower in ("beginner", "начинающий", "базовый"):
                context_lines.append(
                    (self.config.beginner_instructions or "Уровень подготовки: beginner.").strip()
                )
            elif lower in ("advanced", "продвинутый", "углублённый"):
                context_lines.append(
                    (self.config.advanced_instructions or "Уровень подготовки: advanced.").strip()
                )
            else:
                context_lines.append(f"Уровень подготовки: {difficulty}.")
        if course_id:
            context_lines.append(f"Курс ID: {course_id}.")
        if context_lines:
            parts.append("\n".join(["Контекст студента:"] + context_lines))

        # LMS data
        if lms_data:
            parts.append(self._format_lms_data(lms_data))

        # RAG context
        if rag_context:
            parts.append(self._format_rag_context(rag_context))

        # Few-shot examples
        parts.append(self.config.few_shot_examples or self._few_shot_examples())

        # Conversation history (shortened)
        if history:
            parts.append(self._format_history(history, max_messages=self.config.max_history_messages or 6))

        # User question
        parts.append(f"Вопрос студента:\n{message}")

        # Output rules
        parts.append(self.config.output_rules or self._output_rules())

        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _format_lms_data(lms_data: Dict[str, Any]) -> str:
        lines = ["Данные из LMS:"]
        contents = lms_data.get("contents", [])
        if contents:
            lines.append("Структура курса (модули и уроки):")
            current_section = None
            for item in contents[:30]:
                section = item.get("section_name") or "Раздел"
                if section != current_section:
                    lines.append(f"\n### {section}")
                    current_section = section
                name = item.get("name", "Без названия")
                modname = item.get("modname", "")
                url = item.get("url", "-")
                lines.append(f"- {name} ({modname}) — {url}")
        deadlines = lms_data.get("deadlines", [])
        if deadlines:
            lines.append("\nБлижайшие дедлайны:")
            for d in deadlines[:10]:
                due = d.get("due_date") or "нет даты"
                lines.append(f"- {d.get('name', 'Без названия')}: {due} (URL: {d.get('url', '-')})")
        progress = lms_data.get("progress", {})
        if progress:
            lines.append(
                f"\nПрогресс курса: {progress.get('completion_status', 'нет данных')}. "
                f"Общая оценка: {progress.get('overall_grade_formatted', '-')}."
            )
        return "\n".join(lines)

    @staticmethod
    def _format_rag_context(rag_context: List[Dict[str, Any]]) -> str:
        lines = ["Релевантные фрагменты из Knowledge Base (используй ТОЛЬКО эти идентификаторы в разделе Источники):"]
        for i, chunk in enumerate(rag_context, start=1):
            meta = chunk.get("metadata", {})
            doc_id = meta.get("document_id", "?")
            chunk_idx = meta.get("chunk_index", "?")
            difficulty = meta.get("difficulty", "?")
            lines.append(
                f"[Фрагмент KB-{doc_id}-{chunk_idx}] "
                f"document_id={doc_id} chunk_index={chunk_idx} difficulty={difficulty}:\n"
                f"{chunk.get('content', '')}"
            )
        return "\n\n".join(lines)

    @staticmethod
    def _few_shot_examples() -> str:
        return """Примеры правильных и неправильных ответов:

Вопрос: Когда дедлайн по заданию Claude Code Setup?
Правильно: Дедлайн по заданию «Claude Code Setup» — 5 августа 2026 г., 23:55. Ссылка на задание: <LMS URL>.
Неправильно: Я думаю, что дедлайн где-то на следующей неделе.

Вопрос: Сколько уроков в курсе?
Правильно: В курсе 8 уроков: Установка, Интерфейс, Первый диалог, Структура промпта, Ролевые промпты, Chain-of-thought, Автоматизация, Интеграция. Ссылки на уроки: <LMS URL>.
Неправильно: Я не знаю, сколько уроков.

Вопрос: Объясни, что такое промпт-инжиниринг.
Правильно: Промпт-инжиниринг — это процесс составления эффективных запросов к языковым моделям. Подробнее в лекции «Промпты и Claude» (ссылка).
Неправильно: Это когда ты хакер и ломаешь нейросеть."""

    @staticmethod
    def _format_history(history: List[Dict[str, str]], max_messages: int = 6) -> str:
        lines = ["История диалога (последние сообщения):"]
        for entry in history[-max_messages:]:
            speaker = "Студент" if entry.get("role") == "user" else "AI Curator"
            lines.append(f"{speaker}: {entry.get('content', '')}")
        return "\n".join(lines)

    @staticmethod
    def _output_rules() -> str:
        return """Правила оформления ответа:
1. Отвечай кратко и по делу, но с достаточным пояснением.
2. Используй markdown (заголовки, списки, выделение).
3. В разделе «Источники» указывай ТОЛЬКО те материалы, которые реально использованы для ответа. Не добавляй в источники уроки или задания, которые не упоминаются в тексте ответа.
4. Для источников Knowledge Base указывай ID документа в формате: «Материал Knowledge Base (документ N)».
5. Для уроков курса используй их названия и URL из раздела «Структура курса».
6. Если вопрос касается курса, которого нет в предоставленных данных LMS, напиши: «У меня нет данных об этом курсе. Обратитесь к преподавателю.»
7. Если студент просит выставить оценку, зачёт или перенести дедлайн, вежливо откажи и объясни: «Я не выставляю оценки и не изменяю учебный процесс. Обратитесь к преподавателю.»
8. Не выдумывай факты, не упоминай других студентов.
9. Учитывай уровень подготовки: для beginner — просто и с примерами, для advanced — углублённо и технически.
10. Если предоставленный контекст позволяет ответить — отвечай на основе контекста, не добавляй отказов в конец."""
