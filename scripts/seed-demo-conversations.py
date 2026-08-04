#!/usr/bin/env python3
"""Seed AI Curator with real LLM-generated demo conversations via public API.

This script performs HTTP calls to /api/v1/chat exactly like a real student.
It does NOT use TRUNCATE, DELETE, or direct database writes. It relies on the
backend to persist chat requests, logs, execution sessions, and audit events.
"""

import argparse
import random
import sys
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional

import requests

BASE_URL = "https://curator-api.alex-n8n.site"
CHAT_URL = f"{BASE_URL}/api/v1/chat"


@dataclass
class DemoPersona:
    role: str
    course_ids: List[int]
    sessions: int
    questions_per_session: int


PERSONAS = [
    DemoPersona("active_student", [3, 4], 18, 3),
    DemoPersona("late_student", [3], 12, 3),
    DemoPersona("new_student", [3], 10, 3),
]

QUESTION_BANK = {
    "deadline": [
        "Когда дедлайн по следующему заданию?",
        "Какие ближайшие дедлайны у меня?",
        "До когда нужно сдать задание по промпт-инжинирингу?",
        "Сколько времени осталось до дедлайна?",
        "Какое задание сдаётся раньше всего?",
    ],
    "progress": [
        "Какие модули я уже прошёл?",
        "Какая у меня успеваемость?",
        "Что мне ещё нужно сдать, чтобы завершить курс?",
        "Какие задания я не выполнил?",
        "Сколько процентов курса я прошёл?",
    ],
    "study": [
        "Раскрой тему промпт-инжиниринга.",
        "Что такое цепочка вызовов LLM?",
        "Объясни разницу между списком и словарём.",
        "Как работает n8n workflow?",
        "Расскажи про few-shot prompting.",
        "Что такое embeddings и зачем они нужны?",
    ],
    "organizational": [
        "Сколько всего заданий в курсе?",
        "Расскажи структуру курса.",
        "Какие модули есть в курсе?",
        "Сколько уроков в модуле по Claude Code?",
        "Какой порядок прохождения курса?",
    ],
    "mixed": [
        "До когда сдача задания по промпт-инжинирингу и что это за тема?",
        "Когда дедлайн и как решать задачу на Python?",
        "Сколько времени осталось до сдачи и что повторить?",
        "Какие задания впереди и по каким темам?",
    ],
    "default": [
        "Расскажи что-нибудь полезное про этот курс.",
        "Что важно знать новому студенту?",
        "Как лучше учиться на этом курсе?",
        "Какие темы самые сложные?",
    ],
}

INTENT_ORDER = ["deadline", "progress", "study", "organizational", "mixed", "default"]


def send_question(
    session_id: str,
    role: str,
    course_id: int,
    difficulty: str,
    message: str,
    history: Optional[List[dict]] = None,
) -> dict:
    payload = {
        "session_id": session_id,
        "role": role,
        "course_id": course_id,
        "difficulty": difficulty,
        "message": message,
        "history": history or [],
    }
    response = requests.post(CHAT_URL, json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def run_session(persona: DemoPersona, session_index: int) -> int:
    session_id = str(uuid.uuid4())
    count = 0
    # Pick a deterministic-ish mix of intents per session.
    intents = random.sample(INTENT_ORDER, min(3, len(INTENT_ORDER)))
    # Ensure every session has at least one deadline/progress/study if possible.
    required = [i for i in ["deadline", "progress", "study"] if i not in intents]
    if required:
        intents = (required[:1] + intents)[:3]

    history = []
    for intent in intents:
        course_id = random.choice(persona.course_ids)
        difficulty = random.choice(["beginner", "advanced"])
        question = random.choice(QUESTION_BANK[intent])
        try:
            result = send_question(session_id, persona.role, course_id, difficulty, question, history)
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": result.get("answer", "")[:500]})
            count += 1
            print(f"  [{persona.role}] {intent}: {question[:50]}... -> {result.get('intent', '?')}")
        except requests.HTTPError as exc:
            print(f"  ERROR [{persona.role}] {question[:50]}...: {exc.response.status_code} {exc.response.text[:100]}")
        except Exception as exc:
            print(f"  ERROR [{persona.role}] {question[:50]}...: {exc}")
        time.sleep(1)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed AI Curator demo conversations via public API.")
    parser.add_argument("--max", type=int, default=130, help="Maximum number of questions to send.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds.")
    args = parser.parse_args()

    random.seed(42)
    total = 0
    target = args.max

    print(f"Starting demo conversation seeding. Target: {target} questions. Base URL: {BASE_URL}")

    # Pre-shuffle persona/session schedule to get a natural mix.
    schedule: List[tuple] = []
    for persona in PERSONAS:
        for idx in range(persona.sessions):
            schedule.append((persona, idx))
    random.shuffle(schedule)

    for persona, session_index in schedule:
        if total >= target:
            break
        expected = min(persona.questions_per_session, target - total)
        print(f"\nSession {session_index + 1}/{persona.sessions} for {persona.role} (target {expected} questions)")
        sent = run_session(persona, session_index)
        total += sent
        print(f"Running total: {total}/{target}")

    print(f"\nDone. Sent {total} real chat requests to {BASE_URL}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
