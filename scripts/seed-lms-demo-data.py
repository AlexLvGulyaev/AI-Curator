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
    course3_done_assignments: List[int]  # mdl_assign.id values for course 3
    course4_done_assignments: List[int]  # mdl_assign.id values for course 4
    grades: dict[int, float]             # mdl_assign.id -> grade


DEMO_USERS: List[DemoUser] = [
    DemoUser(
        user_id=10,
        role="active_student",
        course3_done_assignments=[10, 11, 12],
        course4_done_assignments=[],  # filled at runtime after course 4 assignments are created
        grades={10: 95.0, 11: 92.0, 12: 88.0},
    ),
    DemoUser(
        user_id=11,
        role="late_student",
        course3_done_assignments=[10],
        course4_done_assignments=[],
        grades={10: 70.0},
    ),
    DemoUser(
        user_id=12,
        role="new_student",
        course3_done_assignments=[],
        course4_done_assignments=[],
        grades={},
    ),
]

PROMPT_ENGINEERING_MODULES = [
    "Модуль 1. Основы промпт-инжиниринга",
    "Модуль 2. Ролевые и контекстные промпты",
    "Модуль 3. Chain-of-thought и структурирование",
    "Модуль 4. Итеративная разработка промптов",
    "Модуль 5. Практические применения",
]

PROMPT_ENGINEERING_ASSIGNMENTS = [
    "ДЗ: Введение в промпт-инжиниринг",
    "ДЗ: Ролевые и контекстные промпты",
    "ДЗ: Chain-of-thought",
    "ДЗ: Итеративная разработка промптов",
    "ДЗ: Итоговый проект по промпт-инжинирингу",
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


async def _ensure_prompt_course_assignments(conn: asyncpg.Connection) -> List[int]:
    """Create sections and assignments in the Prompt Engineering course (id=4).

    Returns the list of created/resolved assignment ids.
    """
    course_id = 4
    module_id = await _get_assign_module_id(conn)
    now = int(datetime.now(timezone.utc).timestamp())

    existing = await conn.fetch(
        "SELECT id FROM mdl_assign WHERE course = $1 ORDER BY id", course_id
    )
    expected_count = len(PROMPT_ENGINEERING_ASSIGNMENTS)
    if existing and len(existing) == expected_count:
        return [row["id"] for row in existing]

    # Partial or missing: clean up existing demo assignments in course 4.
    if existing:
        existing_ids = [row["id"] for row in existing]
        for assign_id in existing_ids:
            await conn.execute("DELETE FROM mdl_assign WHERE id = $1", assign_id)
            await conn.execute(
                "DELETE FROM mdl_grade_items WHERE itemmodule = 'assign' AND iteminstance = $1",
                assign_id,
            )
        await conn.execute(
            "DELETE FROM mdl_course_modules WHERE module = $1 AND course = $2 AND instance = ANY($3::bigint[])",
            module_id,
            course_id,
            existing_ids,
        )
        await conn.execute(
            "UPDATE mdl_course_sections SET sequence = '' WHERE course = $1 AND section > 0",
            course_id,
        )

    section_ids: List[int] = []
    for idx, section_name in enumerate(PROMPT_ENGINEERING_MODULES, start=1):
        section_id = await _ensure_course_section(conn, course_id, idx, section_name)
        section_ids.append(section_id)

    assignment_ids: List[int] = []
    for section_idx, (section_name, assign_name) in enumerate(
        zip(PROMPT_ENGINEERING_MODULES, PROMPT_ENGINEERING_ASSIGNMENTS), start=1
    ):
        section_id = section_ids[section_idx - 1]
        duedate = now + (section_idx * 7 * 24 * 3600)

        assign_id = await conn.fetchval(
            "INSERT INTO mdl_assign (course, name, intro, introformat, duedate, grade, "
            "timemodified, allowsubmissionsfromdate, cutoffdate, submissiondrafts, "
            "sendnotifications, sendlatenotifications, completionsubmit, "
            "requiresubmissionstatement, attemptreopenmethod, maxattempts, "
            "markingworkflow, markingallocation, blindmarking, revealidentities, "
            "sendstudentnotifications, submissionattachments) "
            "VALUES ($1, $2, '', 1, $3, 100, $4, 0, 0, 0, 0, 0, 1, 0, 'none', -1, 0, 0, 0, 0, 1, 0) "
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


async def _clear_previous_demo_data(conn: asyncpg.Connection, all_assign_ids: List[int]):
    all_user_ids = [u.user_id for u in DEMO_USERS]
    if not all_assign_ids:
        return

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
        "SELECT id FROM mdl_course_modules WHERE module = (SELECT id FROM mdl_modules WHERE name='assign') "
        "AND instance = ANY($1::bigint[])",
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

    # active_student also completes the first Prompt Engineering assignment.
    for user in DEMO_USERS:
        done_course4 = list(user.course4_done_assignments)
        if user.role == "active_student" and course4_assign_ids:
            done_course4 = [course4_assign_ids[0]]

        for assign_id in user.course3_done_assignments + done_course4:
            grade = user.grades.get(assign_id, 80.0)

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

        await _configure_page_completion(conn, 3)
        await _configure_page_completion(conn, 4)

        all_assign_ids = course3_assign_ids + course4_assign_ids
        await _clear_previous_demo_data(conn, all_assign_ids)
        await _insert_demo_progress(conn, course3_assign_ids, course4_assign_ids)

        print("Demo LMS data seeded successfully.")
        print(f"Course 3 assignments: {course3_assign_ids}")
        print(f"Course 4 assignments: {course4_assign_ids}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
