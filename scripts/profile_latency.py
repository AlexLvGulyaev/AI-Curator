"""Profile chat endpoint latency on the live backend."""

import json
import statistics
import sys
import time
from dataclasses import dataclass
from typing import List

import httpx


@dataclass
class ProfileCase:
    name: str
    message: str
    role: str
    difficulty: str
    course_id: int


CASES = [
    ProfileCase(
        "organizational_deadline",
        "Когда нужно сдать третье задание по курсу Claude Code?",
        "active_student",
        "beginner",
        3,
    ),
    ProfileCase(
        "study_basic",
        "Объясни разницу между списком и словарём в Python.",
        "active_student",
        "beginner",
        3,
    ),
    ProfileCase(
        "study_advanced",
        "Объясни разницу между списком и словарём в Python.",
        "active_student",
        "advanced",
        3,
    ),
    ProfileCase(
        "mixed_revision",
        "Что мне повторить перед заданием, которое нужно сдать в пятницу?",
        "active_student",
        "beginner",
        3,
    ),
    ProfileCase(
        "progress",
        "Какие модули я уже прошёл?",
        "active_student",
        "beginner",
        3,
    ),
    ProfileCase(
        "refusal_grade",
        "Выставь мне зачёт по третьему заданию.",
        "active_student",
        "beginner",
        3,
    ),
]


def call_backend(case: ProfileCase, base_url: str = "http://localhost:8000") -> dict:
    payload = {
        "message": case.message,
        "role": case.role,
        "difficulty": case.difficulty,
        "course_id": case.course_id,
    }
    url = f"{base_url}/api/v1/chat"
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        print(f"HTTP error for {case.name}: {exc}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as exc:
        print(f"JSON error for {case.name}: {exc}", file=sys.stderr)
        return {}


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"Profiling AI Curator chat latency on {base_url}")
    print("=" * 60)
    for case in CASES:
        latencies: List[float] = []
        intents: List[str] = []
        print(f"\nCase: {case.name} | difficulty={case.difficulty}")
        for i in range(5):
            start = time.perf_counter()
            data = call_backend(case, base_url=base_url)
            wall_ms = round((time.perf_counter() - start) * 1000, 2)
            latency_ms = data.get("latency_ms")
            if latency_ms is None:
                latency_ms = wall_ms
            intent = data.get("intent", "unknown")
            latencies.append(latency_ms)
            intents.append(intent)
            print(f"  run {i+1}: intent={intent} latency_ms={latency_ms} wall_ms={wall_ms}")
        print(f"  summary: p50={statistics.median(latencies):.2f} mean={statistics.mean(latencies):.2f} max={max(latencies):.2f}")


if __name__ == "__main__":
    main()
