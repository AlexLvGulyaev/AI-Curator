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
            lines.append("Структура курса (модули и уроки). "
                         "Считай количество модулей ТОЛЬКО по уникальным названиям разделов ниже, "
                         "а не по количеству уроков. Не объединяй и не разделяй модули самостоятельно.")
            current_section = None
            for item in contents[:22]:
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
            for d in deadlines[:5]:
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
        return """Формат ответа:

Вопрос: Когда дедлайн по заданию Claude Code Setup?
Ответ: Дедлайн по заданию «Claude Code Setup» — 5 августа 2026 г., 23:55. Ссылка: <LMS URL>.

Вопрос: Сколько уроков в курсе?
Ответ: В курсе 8 уроков: Установка, Интерфейс, Первый диалог, Структура промпта, Ролевые промпты, Chain-of-thought, Автоматизация, Интеграция. Ссылки: <LMS URL>.

Вопрос: Объясни, что такое промпт-инжиниринг.
Ответ: Промпт-инжиниринг — это процесс составления эффективных запросов к языковым моделям."""

    @staticmethod
    def _format_history(history: List[Dict[str, str]], max_messages: int = 6) -> str:
        lines = ["История диалога (последние сообщения):"]
        for entry in history[-max_messages:]:
            speaker = "Студент" if entry.get("role") == "user" else "AI Curator"
            lines.append(f"{speaker}: {entry.get('content', '')}")
        return "\n".join(lines)

    @staticmethod
    def _output_rules() -> str:
        return """Правила ответа:
1. Отвечай кратко, по существу, на русском языке.
2. Используй markdown.
3. Источники — только реально использованные материалы.
4. KB-источники: «Материал Knowledge Base (документ N)».
5. LMS-источники: название урока/задания + URL.
6. Если курса нет в данных: «У меня нет данных об этом курсе. Обратитесь к преподавателю.»
7. На запросы об ИЗМЕНЕНИИ оценок или дедлайнов (перенеси, продли, выставь, измени): «Я не выставляю оценки и не изменяю учебный процесс. Обратитесь к преподавателю.» — но отвечай на вопросы ПРОСМОТРА дедлайнов и оценок на основе данных LMS.
8. Не выдумывай факты, не упоминай других студентов.
9. Учитывай уровень подготовки: beginner — просто с примерами, advanced — углублённо.
10. Отвечай на основе контекста, не добавляй отказов в конец."""
