"""AI Configuration business logic and default seed."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_config import AiConfig

DEFAULT_SYSTEM_PROMPT = """Ты — AI Curator, цифровой наставник студентов.

Твоя задача — помогать студентам ориентироваться в учебном процессе, разбирать сложные темы и находить ответы в учебных материалах.

Правила:
- Отвечай в поддерживающем, понятном стиле.
- Запрещено выставлять оценки, изменять дедлайны, задания или расписание.
- Каждый факт должен быть подкреплён источником: либо материалом Knowledge Base, либо данными LMS.
- Если информации недостаточно — честно скажи об этом и предложи обратиться к преподавателю.
- Не раскрывай персональные данные других студентов.
- Используй markdown для структуры ответа: списки, выделение, короткие абзацы."""

DEFAULT_BEGINNER_INSTRUCTIONS = (
    "Уровень подготовки: beginner. "
    "Объясняй простыми словами, избегай жаргона, давай конкретные примеры, используй аналогии. "
    "Не углубляйся в технические детали. "
    "Обязательно отвечай на основе предоставленных материалов; если контекст неполный — всё равно дай краткий ответ на том, что есть. "
    "Не отказывайся от ответа, когда предоставлен релевантный контекст."
)

DEFAULT_ADVANCED_INSTRUCTIONS = (
    "Уровень подготовки: advanced. "
    "Давай углублённый ответ: детали реализации, edge cases, сравнения подходов, практические нюансы. "
    "Примеры должны быть более техническими."
)

DEFAULT_OUTPUT_RULES = """Правила оформления ответа:
1. Отвечай кратко и по делу, но с достаточным пояснением.
2. Используй markdown (заголовки, списки, выделение).
3. В разделе «Источники» указывай ТОЛЬКО те материалы, которые реально использованы для ответа.
4. Для источников Knowledge Base указывай ID документа в формате: «Материал Knowledge Base (документ N)».
5. Для уроков курса используй их названия и URL из раздела «Структура курса».
6. Если вопрос касается курса, которого нет в предоставленных данных LMS, напиши: «У меня нет данных об этом курсе. Обратитесь к преподавателю.»
7. Если студент просит выставить оценку, зачёт или перенести дедлайн, вежливо откажи и объясни: «Я не выставляю оценки и не изменяю учебный процесс. Обратитесь к преподавателю.»
8. Не выдумывай факты, не упоминай других студентов.
9. Учитывай уровень подготовки.
10. Если предоставленный контекст позволяет ответить — отвечай на основе контекста, не добавляй отказов в конец."""

DEFAULT_FEW_SHOT_EXAMPLES = """Примеры правильных и неправильных ответов:

Вопрос: Когда дедлайн по заданию Claude Code Setup?
Правильно: Дедлайн по заданию «Claude Code Setup» — 5 августа 2026 г., 23:55. Ссылка на задание: <LMS URL>.
Неправильно: Я думаю, что дедлайн где-то на следующей неделе.

Вопрос: Сколько уроков в курсе?
Правильно: В курсе 8 уроков: Установка, Интерфейс, Первый диалог, Структура промпта, Ролевые промпты, Chain-of-thought, Автоматизация, Интеграция. Ссылки на уроки: <LMS URL>.
Неправильно: Я не знаю, сколько уроков.

Вопрос: Объясни, что такое промпт-инжиниринг.
Правильно: Промпт-инжиниринг — это процесс составления эффективных запросов к языковым моделям. Подробнее в лекции «Промпты и Claude» (ссылка).
Неправильно: Это когда ты хакер и ломаешь нейросеть."""

DEFAULT_REFUSAL_ANSWER_TEXT = (
    "Я не выставляю оценки и не изменяю учебный процесс. Обратитесь к преподавателю."
)


class AiConfigService:
    """Service for managing versioned AI configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> AiConfig:
        """Return the active AI config or create a default one if missing.

        If the active config exists but its optional instruction fields are empty,
        fall back to the default values so that out-of-the-box deployments behave
        consistently.
        """
        stmt = select(AiConfig).where(AiConfig.is_active == True)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()
        if config is None:
            config = AiConfig(
                name="Default",
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=1024,
                top_k_retrieval=5,
                rag_distance_threshold=1.35,
                beginner_instructions=DEFAULT_BEGINNER_INSTRUCTIONS,
                advanced_instructions=DEFAULT_ADVANCED_INSTRUCTIONS,
                few_shot_examples=DEFAULT_FEW_SHOT_EXAMPLES,
                output_rules=DEFAULT_OUTPUT_RULES,
                refusal_answer_text=DEFAULT_REFUSAL_ANSWER_TEXT,
                max_history_messages=6,
                is_active=True,
                created_by="system",
            )
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)
        else:
            # Backfill missing optional instruction fields with sane defaults.
            updated = False
            if not config.beginner_instructions:
                config.beginner_instructions = DEFAULT_BEGINNER_INSTRUCTIONS
                updated = True
            if not config.advanced_instructions:
                config.advanced_instructions = DEFAULT_ADVANCED_INSTRUCTIONS
                updated = True
            if updated:
                await self.db.commit()
                await self.db.refresh(config)
        return config

    async def list_configs(self, limit: int = 100, offset: int = 0) -> List[AiConfig]:
        """Return all configuration versions ordered by creation date desc."""
        stmt = (
            select(AiConfig)
            .order_by(AiConfig.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique())

    async def create_config(
        self,
        name: str,
        system_prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        top_k_retrieval: int,
        rag_distance_threshold: float = 1.35,
        beginner_instructions: Optional[str] = None,
        advanced_instructions: Optional[str] = None,
        few_shot_examples: Optional[str] = None,
        output_rules: Optional[str] = None,
        refusal_answer_text: Optional[str] = None,
        max_history_messages: int = 6,
        created_by: Optional[str] = None,
    ) -> AiConfig:
        """Create a new configuration version as inactive."""
        config = AiConfig(
            name=name,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_k_retrieval=top_k_retrieval,
            rag_distance_threshold=rag_distance_threshold,
            beginner_instructions=beginner_instructions or DEFAULT_BEGINNER_INSTRUCTIONS,
            advanced_instructions=advanced_instructions or DEFAULT_ADVANCED_INSTRUCTIONS,
            few_shot_examples=few_shot_examples or DEFAULT_FEW_SHOT_EXAMPLES,
            output_rules=output_rules or DEFAULT_OUTPUT_RULES,
            refusal_answer_text=refusal_answer_text or DEFAULT_REFUSAL_ANSWER_TEXT,
            max_history_messages=max_history_messages,
            is_active=False,
            created_by=created_by,
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def activate(self, config_id: int) -> AiConfig:
        """Activate the given config and deactivate all others."""
        all_configs = await self.list_configs(limit=1000)
        target = None
        for config in all_configs:
            config.is_active = config.id == config_id
            if config.id == config_id:
                target = config
        if target is None:
            raise ValueError(f"AI config {config_id} not found")
        await self.db.commit()
        await self.db.refresh(target)
        return target
