#!/usr/bin/env python3
"""Seed demo LMS data for AI Curator E2E scenarios.

This script populates the Moodle database with:
- A full Prompt Engineering course (course id=4) with 5 sections and 5 assignments.
- Submissions, grades and completion records for active_student, late_student
  and new_student so that each role has a clearly distinguishable progress profile.

The script is idempotent for the target demo users.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import asyncpg


@dataclass
class DemoUser:
    user_id: int
    role: str
    course3_done_count: int  # number of first assignments completed in course 3
    course4_done_count: int  # number of first assignments completed in course 4
    grades: dict[int, float]  # mdl_assign.id -> grade


DEMO_USERS: List[DemoUser] = [
    DemoUser(
        user_id=10,
        role="active_student",
        course3_done_count=3,
        course4_done_count=3,
        grades={},
    ),
    DemoUser(
        user_id=11,
        role="late_student",
        course3_done_count=1,
        course4_done_count=0,
        grades={},
    ),
    DemoUser(
        user_id=12,
        role="new_student",
        course3_done_count=0,
        course4_done_count=0,
        grades={},
    ),
]


def _default_grade(index: int) -> float:
    # Vary default grades so progress profiles look realistic.
    defaults = [95.0, 92.0, 88.0, 85.0, 90.0]
    return defaults[index % len(defaults)]


PROMPT_ENGINEERING_MODULES = [
    "Модуль 1. Основы промпт-инжиниринга",
    "Модуль 2. Ролевые и контекстные промпты",
    "Модуль 3. Chain-of-thought и структурирование",
    "Модуль 4. Итеративная разработка промптов",
    "Модуль 5. Практические применения",
]

PROMPT_ENGINEERING_PAGES: List[List[str]] = [
    [
        "PE01. Что такое промпт",
        "PE02. Базовые компоненты запроса",
        "PE03. Чего избегать при написании промптов",
    ],
    [
        "PE04. Ролевые промпты",
        "PE05. Контекстные промпты",
        "PE06. Комбинация роли и контекста",
    ],
    [
        "PE07. Chain-of-thought",
        "PE08. Zero-shot и few-shot",
        "PE09. Структурирование сложных запросов",
    ],
    [
        "PE10. Итеративная разработка",
        "PE11. Обработка ошибок",
        "PE12. Этика и безопасность",
    ],
    [
        "PE13. Промпты в бизнесе",
        "PE14. Промпты в образовании",
        "PE15. Итоговый проект",
    ],
]

PROMPT_ENGINEERING_ASSIGNMENTS: List[str] = [
    "ДЗ: PE01. Что такое промпт",
    "ДЗ: PE02. Базовые компоненты запроса",
    "ДЗ: PE03. Чего избегать при написании промптов",
    "ДЗ: PE04. Ролевые промпты",
    "ДЗ: PE05. Контекстные промпты",
    "ДЗ: PE06. Комбинация роли и контекста",
    "ДЗ: PE07. Chain-of-thought",
    "ДЗ: PE08. Zero-shot и few-shot",
    "ДЗ: PE09. Структурирование сложных запросов",
    "ДЗ: PE10. Итеративная разработка",
    "ДЗ: PE11. Обработка ошибок",
    "ДЗ: PE12. Этика и безопасность",
    "ДЗ: PE13. Промпты в бизнесе",
    "ДЗ: PE14. Промпты в образовании",
    "ДЗ: PE15. Итоговый проект",
]


async def _get_assign_module_id(conn: asyncpg.Connection) -> int:
    row = await conn.fetchrow("SELECT id FROM mdl_modules WHERE name = 'assign'")
    if row is None:
        raise RuntimeError("assign module not found in mdl_modules")
    return row["id"]


async def _ensure_course_section(conn: asyncpg.Connection, course_id: int, section_num: int, name: str) -> int:
    row = await conn.fetchrow(
        "SELECT id FROM mdl_course_sections WHERE course = $1 AND section = $2",
        course_id,
        section_num,
    )
    now = int(datetime.now(timezone.utc).timestamp())
    if row:
        await conn.execute(
            "UPDATE mdl_course_sections SET name = $1, timemodified = $2 WHERE id = $3",
            name,
            now,
            row["id"],
        )
        return row["id"]
    new_row = await conn.fetchrow(
        "INSERT INTO mdl_course_sections (course, section, name, sequence, visible, timemodified) "
        "VALUES ($1, $2, $3, '', 1, $4) RETURNING id",
        course_id,
        section_num,
        name,
        now,
    )
    return new_row["id"]


async def _ensure_page_module_id(conn: asyncpg.Connection) -> int:
    row = await conn.fetchrow("SELECT id FROM mdl_modules WHERE name = 'page'")
    if row is None:
        raise RuntimeError("page module not found in mdl_modules")
    return row["id"]


async def _ensure_course_pages(
    conn: asyncpg.Connection,
    course_id: int,
    section_ids: List[int],
    page_names_by_section: List[List[str]],
) -> List[int]:
    """Create or update page modules inside each section. Return created cm ids."""
    page_module_id = await _ensure_page_module_id(conn)
    now = int(datetime.now(timezone.utc).timestamp())
    created_cm_ids: List[int] = []

    for section_idx, section_id in enumerate(section_ids):
        page_names = page_names_by_section[section_idx]
        for page_name in page_names:
            # Check if a page with this name already exists in this section.
            existing = await conn.fetchrow(
                "SELECT cm.id AS cmid, p.id AS pageid "
                "FROM mdl_course_modules cm "
                "JOIN mdl_page p ON p.id = cm.instance "
                "WHERE cm.course = $1 AND cm.module = $2 AND cm.section = $3 AND p.name = $4",
                course_id,
                page_module_id,
                section_id,
                page_name,
            )
            if existing:
                created_cm_ids.append(existing["cmid"])
                continue

            page_id = await conn.fetchval(
                "INSERT INTO mdl_page (id, course, name, intro, introformat, content, "
                "contentformat, display, displayoptions, timemodified, legacyfiles, "
                "revision) "
                "VALUES (nextval('mdl_page_id_seq'), $1, $2, '', 1, $3, 1, 5, 'null', $4, 0, 1) RETURNING id",
                course_id,
                page_name,
                f"<p>Содержимое урока <b>{page_name}</b>.</p>",
                now,
            )
            cm_id = await conn.fetchval(
                "INSERT INTO mdl_course_modules (course, module, instance, section, added, "
                "visible, completion, completionview) "
                "VALUES ($1, $2, $3, $4, $5, 1, 2, 1) RETURNING id",
                course_id,
                page_module_id,
                page_id,
                section_id,
                now,
            )
            current_seq = await conn.fetchval(
                "SELECT sequence FROM mdl_course_sections WHERE id = $1", section_id
            )
            items = [x for x in (current_seq or "").split(",") if x]
            items.append(str(cm_id))
            await conn.execute(
                "UPDATE mdl_course_sections SET sequence = $1 WHERE id = $2",
                ",".join(items),
                section_id,
            )
            created_cm_ids.append(cm_id)
    return created_cm_ids


async def _ensure_prompt_course_assignments(conn: asyncpg.Connection) -> List[int]:
    """Create sections and assignments in the Prompt Engineering course (id=4).

    Each page lesson gets its own assignment. Assignments are appended after pages
    in each section, matching the structure of course 3.
    Returns the list of created/resolved assignment ids.
    """
    course_id = 4
    module_id = await _get_assign_module_id(conn)
    now = int(datetime.now(timezone.utc).timestamp())

    # Always rebuild assignments so structure stays in sync with pages.
    await conn.execute("DELETE FROM mdl_assign WHERE course = $1", course_id)
    await conn.execute(
        "DELETE FROM mdl_grade_items WHERE itemmodule = 'assign' AND courseid = $1",
        course_id,
    )
    await conn.execute(
        "DELETE FROM mdl_course_modules WHERE module = $1 AND course = $2",
        module_id,
        course_id,
    )
    # Keep pages in sequence, drop assignments.
    await conn.execute(
        "UPDATE mdl_course_sections SET sequence = $1 WHERE course = $2 AND section > 0",
        "",
        course_id,
    )

    # Rebuild section sequence with pages only first.
    page_module_id = await _ensure_page_module_id(conn)
    section_ids: List[int] = []
    for idx, section_name in enumerate(PROMPT_ENGINEERING_MODULES, start=1):
        section_id = await _ensure_course_section(conn, course_id, idx, section_name)
        section_ids.append(section_id)

    # Fetch existing pages for course 4 ordered by id (creation order matches lesson order).
    page_rows = await conn.fetch(
        "SELECT p.id AS pageid, p.name, cm.id AS cmid, cm.section "
        "FROM mdl_course_modules cm "
        "JOIN mdl_page p ON p.id = cm.instance "
        "WHERE cm.course = $1 AND cm.module = $2 AND cm.section = ANY($3::bigint[]) "
        "ORDER BY p.id",
        course_id,
        page_module_id,
        section_ids,
    )
    page_order = [(r["cmid"], r["section"], r["name"]) for r in page_rows]

    assignment_ids: List[int] = []
    for page_cmid, section_id, page_name in page_order:
        assign_name = page_name.replace("PE", "ДЗ: PE")
        duedate = now + ((len(assignment_ids) + 1) * 3 * 24 * 3600)

        assign_id = await conn.fetchval(
            "INSERT INTO mdl_assign (id, course, name, intro, introformat, duedate, grade, "
            "timemodified, allowsubmissionsfromdate, cutoffdate, submissiondrafts, "
            "sendnotifications, sendlatenotifications, completionsubmit, "
            "requiresubmissionstatement, attemptreopenmethod, maxattempts, "
            "markingworkflow, markingallocation, blindmarking, revealidentities, "
            "sendstudentnotifications, submissionattachments) "
            "VALUES (nextval('mdl_assign_id_seq'), $1, $2, '', 1, $3, 100, $4, 0, 0, 0, 0, 0, 1, 0, 'none', -1, 0, 0, 0, 0, 1, 0) "
            "RETURNING id",
            course_id,
            assign_name,
            duedate,
            now,
        )

        cm_id = await conn.fetchval(
            "INSERT INTO mdl_course_modules (course, module, instance, section, added, "
            "visible, completion, completiongradeitemnumber) "
            "VALUES ($1, $2, $3, $4, $5, 1, 2, 0) RETURNING id",
            course_id,
            module_id,
            assign_id,
            section_id,
            now,
        )

        # Sequence: append page then assignment for each lesson.
        current_seq = await conn.fetchval(
            "SELECT sequence FROM mdl_course_sections WHERE id = $1", section_id
        )
        items = [x for x in (current_seq or "").split(",") if x]
        if str(page_cmid) not in items:
            items.append(str(page_cmid))
        items.append(str(cm_id))
        await conn.execute(
            "UPDATE mdl_course_sections SET sequence = $1 WHERE id = $2",
            ",".join(items),
            section_id,
        )

        existing_item = await conn.fetchval(
            "SELECT id FROM mdl_grade_items WHERE itemtype = 'mod' AND itemmodule = 'assign' "
            "AND iteminstance = $1 AND courseid = $2",
            assign_id,
            course_id,
        )
        if existing_item:
            await conn.execute(
                "UPDATE mdl_grade_items SET itemname = $1, timemodified = $2 WHERE id = $3",
                assign_name,
                now,
                existing_item,
            )
        else:
            await conn.execute(
                "INSERT INTO mdl_grade_items (courseid, itemname, itemtype, itemmodule, "
                "iteminstance, itemnumber, gradetype, grademax, grademin, "
                "aggregationcoef, aggregationcoef2, sortorder, display, hidden, locked, "
                "locktime, needsupdate, timecreated, timemodified) "
                "VALUES ($1, $2, 'mod', 'assign', $3, 0, 1, 100, 0, "
                "0, 0, 0, 0, 0, 0, 0, 0, $4, $4)",
                course_id,
                assign_name,
                assign_id,
                now,
            )

        assignment_ids.append(assign_id)

    return assignment_ids


async def _clear_previous_demo_data(conn: asyncpg.Connection, all_assign_ids: List[int], course_ids: List[int]):
    all_user_ids = [u.user_id for u in DEMO_USERS]

    await conn.execute(
        "DELETE FROM mdl_assign_submission WHERE assignment = ANY($1::bigint[]) AND userid = ANY($2::bigint[])",
        all_assign_ids,
        all_user_ids,
    )
    await conn.execute(
        "DELETE FROM mdl_assign_grades WHERE assignment = ANY($1::bigint[]) AND userid = ANY($2::bigint[])",
        all_assign_ids,
        all_user_ids,
    )

    grade_item_ids = await conn.fetch(
        "SELECT id FROM mdl_grade_items WHERE itemmodule = 'assign' AND iteminstance = ANY($1::bigint[])",
        all_assign_ids,
    )
    item_ids = [r["id"] for r in grade_item_ids]
    if item_ids:
        await conn.execute(
            "DELETE FROM mdl_grade_grades WHERE itemid = ANY($1::bigint[]) AND userid = ANY($2::bigint[])",
            item_ids,
            all_user_ids,
        )

    cm_rows = await conn.fetch(
        "SELECT id FROM mdl_course_modules WHERE course = ANY($1::bigint[]) AND "
        "module = (SELECT id FROM mdl_modules WHERE name='assign') AND instance = ANY($2::bigint[])",
        course_ids,
        all_assign_ids,
    )
    cm_ids = [r["id"] for r in cm_rows]
    if cm_ids:
        await conn.execute(
            "DELETE FROM mdl_course_modules_completion WHERE coursemoduleid = ANY($1::bigint[]) "
            "AND userid = ANY($2::bigint[])",
            cm_ids,
            all_user_ids,
        )

    # Also clear page completion for demo users in the rebuilt courses.
    page_cm_rows = await conn.fetch(
        "SELECT id FROM mdl_course_modules WHERE course = ANY($1::bigint[]) AND "
        "module = (SELECT id FROM mdl_modules WHERE name='page')",
        course_ids,
    )
    page_cm_ids = [r["id"] for r in page_cm_rows]
    if page_cm_ids:
        await conn.execute(
            "DELETE FROM mdl_course_modules_completion WHERE coursemoduleid = ANY($1::bigint[]) "
            "AND userid = ANY($2::bigint[])",
            page_cm_ids,
            all_user_ids,
        )


async def _insert_demo_progress(
    conn: asyncpg.Connection,
    course3_assign_ids: List[int],
    course4_assign_ids: List[int],
):
    now = int(datetime.now(timezone.utc).timestamp())
    all_assign_ids = course3_assign_ids + course4_assign_ids

    cm_rows = await conn.fetch(
        "SELECT instance, id FROM mdl_course_modules WHERE module = (SELECT id FROM mdl_modules WHERE name='assign') "
        "AND instance = ANY($1::bigint[])",
        all_assign_ids,
    )
    assign_cm_map = {r["instance"]: r["id"] for r in cm_rows}

    for user in DEMO_USERS:
        done_course3 = course3_assign_ids[: user.course3_done_count]
        done_course4 = course4_assign_ids[: user.course4_done_count]

        for idx, assign_id in enumerate(done_course3 + done_course4):
            grade = user.grades.get(assign_id, _default_grade(idx))

            await conn.execute(
                "INSERT INTO mdl_assign_submission (assignment, userid, timecreated, timemodified, "
                "status, groupid, attemptnumber, latest) "
                "VALUES ($1, $2, $3, $3, 'submitted', 0, 0, 1)",
                assign_id,
                user.user_id,
                now,
            )
            await conn.execute(
                "INSERT INTO mdl_assign_grades (assignment, userid, timecreated, timemodified, "
                "grade, grader, attemptnumber) VALUES ($1, $2, $3, $3, $4, -1, 0)",
                assign_id,
                user.user_id,
                now,
                grade,
            )

            grade_item_id = await conn.fetchval(
                "SELECT id FROM mdl_grade_items WHERE itemmodule = 'assign' AND iteminstance = $1",
                assign_id,
            )
            if grade_item_id:
                existing_gg = await conn.fetchval(
                    "SELECT id FROM mdl_grade_grades WHERE itemid = $1 AND userid = $2",
                    grade_item_id,
                    user.user_id,
                )
                if existing_gg:
                    await conn.execute(
                        "UPDATE mdl_grade_grades SET rawgrade = $1, finalgrade = $1, "
                        "timemodified = $2 WHERE id = $3",
                        grade,
                        now,
                        existing_gg,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO mdl_grade_grades (itemid, userid, rawgrade, rawgrademax, rawgrademin, "
                        "finalgrade, usermodified, timecreated, timemodified, aggregationstatus) "
                        "VALUES ($1, $2, $3, 100, 0, $3, -1, $4, $4, 'used')",
                        grade_item_id,
                        user.user_id,
                        grade,
                        now,
                    )

            cm_id = assign_cm_map.get(assign_id)
            if cm_id:
                existing_comp = await conn.fetchval(
                    "SELECT id FROM mdl_course_modules_completion WHERE coursemoduleid = $1 AND userid = $2",
                    cm_id,
                    user.user_id,
                )
                if existing_comp:
                    await conn.execute(
                        "UPDATE mdl_course_modules_completion SET completionstate = 1, timemodified = $1 WHERE id = $2",
                        now,
                        existing_comp,
                    )
                else:
                    await conn.execute(
                        "INSERT INTO mdl_course_modules_completion (coursemoduleid, userid, "
                        "completionstate, timemodified) VALUES ($1, $2, 1, $3)",
                        cm_id,
                        user.user_id,
                        now,
                    )


async def _configure_page_completion(conn: asyncpg.Connection, course_id: int):
    page_module_id = await conn.fetchval("SELECT id FROM mdl_modules WHERE name = 'page'")
    if page_module_id:
        await conn.execute(
            "UPDATE mdl_course_modules SET completion = 2, completionview = 1 "
            "WHERE course = $1 AND module = $2",
            course_id,
            page_module_id,
        )


async def main():
    db_url = os.environ.get(
        "LMS_DB_URL",
        "postgresql://moodle:MDBP3hfpf2100@ai-curator-lms-db:5432/moodle",
    )
    conn = await asyncpg.connect(db_url)
    try:
        course3_rows = await conn.fetch("SELECT id FROM mdl_assign WHERE course = 3 ORDER BY id")
        course3_assign_ids = [r["id"] for r in course3_rows]

        course4_assign_ids = await _ensure_prompt_course_assignments(conn)

        # Re-fetch section ids for course 4 after assignment creation.
        section_rows = await conn.fetch(
            "SELECT id FROM mdl_course_sections WHERE course = 4 AND section > 0 ORDER BY section"
        )
        course4_section_ids = [r["id"] for r in section_rows]
        if len(course4_section_ids) == len(PROMPT_ENGINEERING_PAGES):
            await _ensure_course_pages(
                conn, 4, course4_section_ids, PROMPT_ENGINEERING_PAGES
            )

        await _configure_page_completion(conn, 3)
        await _configure_page_completion(conn, 4)

        all_assign_ids = course3_assign_ids + course4_assign_ids
        await _clear_previous_demo_data(conn, all_assign_ids, [3, 4])
        await _insert_demo_progress(conn, course3_assign_ids, course4_assign_ids)

        print("Demo LMS data seeded successfully.")
        print(f"Course 3 assignments: {course3_assign_ids}")
        print(f"Course 4 assignments: {course4_assign_ids}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
