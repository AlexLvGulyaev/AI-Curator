"""Orchestrator configuration SQLAlchemy model for AI Curator."""

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


DEFAULT_INTENT_RULES = {
    "deadline": {
        "keywords": [
            "дедлайн",
            "когда сдать",
            "до когда",
            "когда нужно сдать",
            "когда сдавать",
            "срок сдачи",
            "срок",
            "когда deadline",
        ],
        "priority": 1,
    },
    "progress": {
        "keywords": [
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
        "priority": 2,
    },
    "study": {
        "keywords": [
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
        "priority": 3,
    },
    "mixed": {
        "conditions": [
            {"and": ["is_org", "is_study"]},
            {"and": ["is_org", "has_keyword", ["модуль", "модули", "структура курса", "из чего состоит курс"]]},
        ],
        "priority": 4,
    },
    "organizational": {
        "keywords": [
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
        "conditions": [{"and": ["is_org"]}],
        "priority": 5,
    },
}

DEFAULT_INTENT_SOURCE_MAP = {
    "deadline": {"lms": True, "rag": False, "strict_course": True},
    "progress": {"lms": True, "rag": False, "strict_course": True},
    "organizational": {"lms": True, "rag": False, "strict_course": True},
    "study": {"lms": False, "rag": True, "strict_course": False},
    "mixed": {"lms": True, "rag": True, "strict_course": True},
}

DEFAULT_NON_COURSE_STARTERS = [
    "когда",
    "сколько",
    "какой",
    "какая",
    "какое",
    "какие",
    "как",
    "что",
    "почему",
    "зачем",
    "где",
    "куда",
    "откуда",
    "кто",
    "чей",
    "чьё",
    "чьи",
    "объясни",
    "расскажи",
    "покажи",
    "скажи",
    "дай",
    "перечисли",
    "укажи",
    "выведи",
    "напиши",
    "сделай",
    "поставь",
    "выставь",
    "перенеси",
    "сообщи",
    "пройди",
    "прочитай",
    "повтори",
    "изучи",
    "опиши",
    "привет",
    "спасибо",
]

DEFAULT_INTENT_MAX_TOKENS = {
    "organizational": 500,
    "study_beginner": 650,
    "mixed": 800,
    "default": 750,
}

DEFAULT_FALLBACK_MESSAGES = {
    "no_lms_data": (
        "В курсе пока нет опубликованных заданий с дедлайнами. "
        "Если вы ожидаете увидеть задание, обратитесь к преподавателю."
    ),
    "no_rag_context": (
        "У меня недостаточно данных, чтобы точно ответить. "
        "Обратитесь к преподавателю."
    ),
    "out_of_scope_course": (
        "У меня нет данных о курсе «{course}» для вашей учётной записи. "
        "Обратитесь к преподавателю."
    ),
}


class OrchestratorConfig(Base):
    """Singleton-ish orchestrator configuration row.

    Only the row with the lowest id is considered effective. The service
    auto-creates a default row if the table is empty. JSON fields store
    intent rules, source routing, token budgets and fallback messages so that
    methodologists can tune routing without deploying new code.
    """

    __tablename__ = "orchestrator_configs"

    intent_rules: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: dict(DEFAULT_INTENT_RULES)
    )
    default_intent: Mapped[str] = mapped_column(
        String(50), nullable=False, default="study"
    )
    intent_source_map: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: dict(DEFAULT_INTENT_SOURCE_MAP)
    )
    non_course_starters: Mapped[list] = mapped_column(
        JSON, nullable=False, default=lambda: list(DEFAULT_NON_COURSE_STARTERS)
    )
    max_lms_contents: Mapped[int] = mapped_column(
        Integer, nullable=False, default=12
    )
    max_lms_deadlines: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )
    intent_max_tokens: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: dict(DEFAULT_INTENT_MAX_TOKENS)
    )
    fallback_messages: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=lambda: dict(DEFAULT_FALLBACK_MESSAGES)
    )
