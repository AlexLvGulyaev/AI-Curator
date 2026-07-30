"""Manual E2E test for chat scenarios #1-#5 from SPEC."""

import textwrap

import httpx


def chat(message: str, role: str = "active_student", difficulty: str = "beginner", course_id: int = 3) -> dict:
    r = httpx.post(
        "http://localhost:8000/api/v1/chat",
        json={"message": message, "role": role, "difficulty": difficulty, "course_id": course_id},
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()


def fmt(label: str, message: str, data: dict) -> None:
    print("=" * 70)
    print(f"{label}")
    print(f"Вопрос: {message}")
    print(
        f"intent={data.get('intent')} | "
        f"latency_ms={data.get('latency_ms')} | "
        f"model={data.get('model')}"
    )
    print("Ответ:")
    print(textwrap.indent(str(data.get("answer", "")), "  "))
    sources = data.get("sources", [])
    if sources:
        print(f"Источники ({len(sources)}):")
        for s in sources:
            print(f"  - {s}")
    else:
        print("Источники: нет")
    print()


SCENARIOS = [
    ("#2 Учебный basic (run 1)", "Объясни разницу между списком и словарём.", "active_student", "beginner", 3),
    ("#2 Учебный basic (run 2)", "Объясни разницу между списком и словарём.", "active_student", "beginner", 3),
    ("#2 Учебный basic (run 3)", "Объясни разницу между списком и словарём.", "active_student", "beginner", 3),
    ("#2 Учебный basic (run 4)", "Объясни разницу между списком и словарём.", "active_student", "beginner", 3),
    ("#2 Учебный basic (run 5)", "Объясни разницу между списком и словарём.", "active_student", "beginner", 3),
    ("#2 Учебный advanced (run 1)", "Объясни разницу между списком и словарём.", "active_student", "advanced", 3),
    ("#2 Учебный advanced (run 2)", "Объясни разницу между списком и словарём.", "active_student", "advanced", 3),
    ("#2 Учебный advanced (run 3)", "Объясни разницу между списком и словарём.", "active_student", "advanced", 3),
]


def main() -> None:
    for label, msg, role, diff, cid in SCENARIOS:
        try:
            data = chat(msg, role, diff, cid)
            fmt(label, msg, data)
        except Exception as exc:
            print(f"{label}: ОШИБКА {exc}\n")


if __name__ == "__main__":
    main()
