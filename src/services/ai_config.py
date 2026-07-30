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
- Используй markdown для структуры ответа: списки, выделение, короткие абзацы.

Формат ответа:
1. Прямой ответ на вопрос.
2. При необходимости — пояснение или пример.
3. Источники в конце: ссылки на материалы Knowledge Base или задания LMS."""


class AiConfigService:
    """Service for managing versioned AI configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active(self) -> AiConfig:
        """Return the active AI config or create a default one if missing."""
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
                is_active=True,
                created_by="system",
            )
            self.db.add(config)
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
