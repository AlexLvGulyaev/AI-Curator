"""Debug prompt assembly for beginner vs advanced study question."""

import asyncio
import textwrap

from db import async_session_factory
from services.ai_config import AiConfigService
from services.prompt_builder import PromptBuilder


async def main():
    async with async_session_factory() as db:
        svc = AiConfigService(db)
        config = await svc.get_active()

        print("=" * 70)
        print("ACTIVE AI CONFIG")
        print(f"  model={config.model}")
        print(f"  temperature={config.temperature}")
        print(f"  max_tokens={config.max_tokens}")
        print(f"  top_k_retrieval={config.top_k_retrieval}")
        print(f"  rag_distance_threshold={config.rag_distance_threshold}")
        print(f"  beginner_instructions={config.beginner_instructions!r}")
        print(f"  advanced_instructions={config.advanced_instructions!r}")
        print(f"  max_history_messages={config.max_history_messages}")
        print()

        builder = PromptBuilder(config)
        message = "Объясни разницу между списком и словарём."

        for difficulty in ("beginner", "advanced"):
            prompt = builder.build(
                message=message,
                role="active_student",
                difficulty=difficulty,
                course_id=3,
                lms_data={},
                rag_context=[
                    {
                        "content": "Список (list) — упорядоченная изменяемая коллекция элементов. Доступ по индексу. Пример: [1, 2, 3].",
                        "metadata": {"document_id": 84, "chunk_index": 0, "difficulty": "beginner"},
                        "distance": 0.31,
                    },
                    {
                        "content": "Словарь (dict) — неупорядоченная коллекция пар ключ-значение. Доступ по ключу. Пример: {'a': 1, 'b': 2}.",
                        "metadata": {"document_id": 77, "chunk_index": 0, "difficulty": "beginner"},
                        "distance": 0.35,
                    },
                    {
                        "content": "Отличие: список индексируется числами, словарь — уникальными ключами.",
                        "metadata": {"document_id": 48, "chunk_index": 0, "difficulty": "beginner"},
                        "distance": 0.42,
                    },
                ],
                history=[],
            )
            print("=" * 70)
            print(f"PROMPT for difficulty={difficulty}")
            print(f"length={len(prompt)} chars")
            print("-" * 70)
            print(textwrap.indent(prompt, "  "))
            print()


if __name__ == "__main__":
    asyncio.run(main())
