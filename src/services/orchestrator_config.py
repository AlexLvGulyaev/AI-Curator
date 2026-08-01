"""Orchestrator configuration business logic and defaults for AI Curator."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.orchestrator_config import (
    DEFAULT_FALLBACK_MESSAGES,
    DEFAULT_INTENT_MAX_TOKENS,
    DEFAULT_INTENT_RULES,
    DEFAULT_INTENT_SOURCE_MAP,
    DEFAULT_NON_COURSE_STARTERS,
    OrchestratorConfig,
)


class OrchestratorConfigService:
    """Service for managing effective orchestrator configuration."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_default(self) -> OrchestratorConfig:
        """Return the effective orchestrator config row, creating defaults if needed."""
        stmt = select(OrchestratorConfig).order_by(OrchestratorConfig.id.asc()).limit(1)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()
        if config is None:
            config = OrchestratorConfig(
                intent_rules=dict(DEFAULT_INTENT_RULES),
                default_intent="study",
                intent_source_map=dict(DEFAULT_INTENT_SOURCE_MAP),
                non_course_starters=list(DEFAULT_NON_COURSE_STARTERS),
                max_lms_contents=12,
                max_lms_deadlines=5,
                intent_max_tokens=dict(DEFAULT_INTENT_MAX_TOKENS),
                fallback_messages=dict(DEFAULT_FALLBACK_MESSAGES),
            )
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)
        return config

    async def update(
        self,
        intent_rules: Optional[dict] = None,
        default_intent: Optional[str] = None,
        intent_source_map: Optional[dict] = None,
        non_course_starters: Optional[list] = None,
        max_lms_contents: Optional[int] = None,
        max_lms_deadlines: Optional[int] = None,
        intent_max_tokens: Optional[dict] = None,
        fallback_messages: Optional[dict] = None,
    ) -> OrchestratorConfig:
        """Update the effective orchestrator config row."""
        config = await self.get_or_create_default()

        # For partial updates we must keep intent_rules and intent_source_map in sync
        # with the persisted values that are *not* being changed in this request.
        effective_rules = intent_rules if intent_rules is not None else config.intent_rules
        effective_map = intent_source_map if intent_source_map is not None else config.intent_source_map
        rules_intents = set(effective_rules.keys())
        map_intents = set(effective_map.keys())
        if rules_intents != map_intents:
            missing = rules_intents ^ map_intents
            raise ValueError(
                f"intent_rules and intent_source_map intents must match, mismatched: {missing}"
            )

        if intent_rules is not None:
            config.intent_rules = intent_rules
        if default_intent is not None:
            config.default_intent = default_intent
        if intent_source_map is not None:
            config.intent_source_map = intent_source_map
        if non_course_starters is not None:
            config.non_course_starters = non_course_starters
        if max_lms_contents is not None:
            config.max_lms_contents = max_lms_contents
        if max_lms_deadlines is not None:
            config.max_lms_deadlines = max_lms_deadlines
        if intent_max_tokens is not None:
            config.intent_max_tokens = intent_max_tokens
        if fallback_messages is not None:
            config.fallback_messages = fallback_messages
        await self.db.commit()
        await self.db.refresh(config)
        return config
