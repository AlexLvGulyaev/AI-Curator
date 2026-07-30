"""Moodle REST API adapter for AI Curator Backend.

The adapter exposes a read-only interface to the LMS. It is responsible for:
- authenticating and authorizing against the LMS REST API;
- calling the allowed Moodle Web Service functions;
- transforming raw LMS JSON into canonical Pydantic models;
- handling errors, timeouts and unavailable LMS gracefully.

It never writes to the LMS, does not call LLMs and does not manage Knowledge Base.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import settings
from schemas.lms import (
    Course,
    CourseModule,
    Deadline,
    GradeItem,
    LMSHealth,
    UserCourseProgress,
)

READ_ONLY_WHITELIST = {
    "core_course_get_courses",
    "core_course_get_contents",
    "mod_assign_get_assignments",
    "gradereport_user_get_grade_items",
    "core_completion_get_activities_completion_status",
    "core_completion_get_course_completion_status",
}


class LMSAdapterError(Exception):
    """Base exception for LMS Adapter failures."""

    pass


class LMSReadOnlyViolationError(LMSAdapterError):
    """Raised when a write-capable Web Service function is requested."""

    pass


class LMSConnectionError(LMSAdapterError):
    """Raised when the LMS is unreachable or times out."""

    pass


class LMSResponseError(LMSAdapterError):
    """Raised when the LMS returns an error JSON or unexpected status."""

    def __init__(self, message: str, *, response_body: Optional[Any] = None):
        super().__init__(message)
        self.response_body = response_body


class MoodleLMSAdapter:
    """Async Moodle REST API client returning canonical domain models."""

    def __init__(
        self,
        base_url: str = settings.lms_base_url,
        api_token: str = settings.lms_api_token,
        timeout: float = 15.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Low-level HTTP helpers
    # ------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError, LMSConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        reraise=True,
    )
    async def _call(
        self,
        wsfunction: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
    ) -> Any:
        """Call a Moodle REST function and return parsed JSON.

        Enforces a read-only whitelist to guarantee the adapter never writes to LMS.
        """
        if wsfunction not in READ_ONLY_WHITELIST:
            raise LMSReadOnlyViolationError(
                f"Web Service function '{wsfunction}' is not in the read-only whitelist."
            )

        params = params or {}
        url = f"{self.base_url}/webservice/rest/server.php"
        request_params = {
            "wstoken": self.api_token,
            "wsfunction": wsfunction,
            "moodlewsrestformat": "json",
            **params,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=request_params)
                else:
                    response = await client.post(url, data=request_params)
        except httpx.TimeoutException as exc:
            raise LMSConnectionError(f"LMS request timed out: {exc}") from exc
        except httpx.ConnectError as exc:
            raise LMSConnectionError(f"Cannot connect to LMS: {exc}") from exc
        except httpx.HTTPError as exc:
            raise LMSConnectionError(f"LMS HTTP error: {exc}") from exc

        if response.status_code >= 400:
            raise LMSResponseError(
                f"LMS returned HTTP {response.status_code}",
                response_body=response.text,
            )

        try:
            data = response.json()
        except Exception as exc:
            raise LMSResponseError(
                "LMS returned non-JSON response",
                response_body=response.text,
            ) from exc

        # Moodle returns errors inside the JSON body with an 'exception' key
        if isinstance(data, dict) and "exception" in data:
            raise LMSResponseError(
                f"LMS error ({data.get('errorcode')}): {data.get('message')}",
                response_body=data,
            )

        return data

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _from_unix(timestamp: Optional[int]) -> Optional[datetime]:
        """Convert a Unix timestamp to UTC datetime, handling 0 as None."""
        if not timestamp:
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    @staticmethod
    def _course_url(course_id: int) -> str:
        return urljoin(settings.lms_base_url, f"/course/view.php?id={course_id}")

    @staticmethod
    def _module_url(cmid: int) -> str:
        return urljoin(settings.lms_base_url, f"/mod/assign/view.php?id={cmid}")

    # ------------------------------------------------------------------
    # Public read methods returning canonical models
    # ------------------------------------------------------------------

    async def health_check(self) -> LMSHealth:
        """Check LMS connectivity by calling a lightweight read function."""
        import time

        start = time.perf_counter()
        try:
            await self._call("core_course_get_courses")
            elapsed_ms = (time.perf_counter() - start) * 1000
            return LMSHealth(status="ok", response_time_ms=round(elapsed_ms, 2))
        except LMSAdapterError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            return LMSHealth(status="error", detail=str(exc), response_time_ms=round(elapsed_ms, 2))

    async def get_courses(self) -> List[Course]:
        """Return all visible courses in canonical form."""
        raw_courses = await self._call("core_course_get_courses")
        if not isinstance(raw_courses, list):
            raise LMSResponseError("Unexpected response shape for core_course_get_courses")

        result: List[Course] = []
        for raw in raw_courses:
            course_id = raw.get("id")
            result.append(
                Course(
                    id=course_id,
                    shortname=raw.get("shortname", ""),
                    fullname=raw.get("fullname", ""),
                    displayname=raw.get("displayname"),
                    summary=raw.get("summary") or None,
                    visible=bool(raw.get("visible", 1)),
                    start_date=self._from_unix(raw.get("startdate")),
                    end_date=self._from_unix(raw.get("enddate")),
                    url=self._course_url(course_id) if course_id else None,
                    raw=raw,
                )
            )
        return result

    async def get_course_contents(self, course_id: int) -> List[CourseModule]:
        """Return the content structure of a course (sections and modules)."""
        raw_sections = await self._call(
            "core_course_get_contents",
            params={"courseid": course_id},
        )
        if not isinstance(raw_sections, list):
            raise LMSResponseError("Unexpected response shape for core_course_get_contents")

        result: List[CourseModule] = []
        for section in raw_sections:
            section_id = section.get("id")
            section_name = section.get("name")
            section_number = section.get("section")
            for module in section.get("modules", []):
                mod_id = module.get("id")
                result.append(
                    CourseModule(
                        id=mod_id,
                        instance_id=module.get("instance"),
                        name=module.get("name", ""),
                        modname=module.get("modname", ""),
                        section_id=section_id,
                        section_name=section_name,
                        section_number=section_number,
                        visible=bool(module.get("visible", 1)),
                        url=module.get("url"),
                        contents=module.get("contents"),
                        description=module.get("description") or None,
                        raw=module,
                    )
                )
        return result

    async def get_assignments(self, course_id: Optional[int] = None) -> List[Deadline]:
        """Return assignment deadlines, optionally filtered by course.

        When course_id is provided only assignments for that course are returned.
        Falls back to parsing course contents when the LMS token lacks enrollment
        or capability for a specific course (common in multi-course setups).
        """
        params: Dict[str, Any] = {}
        if course_id is not None:
            params["courseids[0]"] = course_id

        raw = await self._call("mod_assign_get_assignments", params=params)
        if not isinstance(raw, dict):
            raise LMSResponseError("Unexpected response shape for mod_assign_get_assignments")

        result: List[Deadline] = []
        for course in raw.get("courses", []):
            for assignment in course.get("assignments", []):
                cmid = assignment.get("cmid")
                result.append(
                    Deadline(
                        id=assignment.get("id"),
                        course_id=course.get("id"),
                        module_id=cmid,
                        instance_id=assignment.get("id"),
                        name=assignment.get("name", ""),
                        modname="assign",
                        due_date=self._from_unix(assignment.get("duedate")),
                        allow_submissions_from=self._from_unix(assignment.get("allowsubmissionsfromdate")),
                        cutoff_date=self._from_unix(assignment.get("cutoffdate")),
                        url=self._module_url(cmid) if cmid else None,
                        raw=assignment,
                    )
                )

        # Fallback: if the service token can't see assignments for a specific course
        # (empty list + capability warning), try reading from course contents which
        # is less restrictive and exposes duedate in module customdata.
        if not result and course_id is not None:
            result = await self._get_assignments_from_contents(course_id)
        return result

    async def _get_assignments_from_contents(self, course_id: int) -> List[Deadline]:
        """Build Deadline objects from core_course_get_contents assign modules.

        Moodle's mod_assign_get_assignments requires the calling user to be
        enrolled or have a management capability in the course. When that is not
        the case, the course contents API still lists assign modules and carries
        the due date in the module customdata JSON.
        """
        import json

        raw_sections = await self._call(
            "core_course_get_contents",
            params={"courseid": course_id},
        )
        if not isinstance(raw_sections, list):
            return []

        result: List[Deadline] = []
        for section in raw_sections:
            for module in section.get("modules", []):
                if module.get("modname") != "assign":
                    continue
                cmid = module.get("id")
                instance_id = module.get("instance")
                duedate: Optional[int] = None
                customdata_raw = module.get("customdata")
                if isinstance(customdata_raw, str):
                    try:
                        customdata = json.loads(customdata_raw)
                        duedate = customdata.get("duedate")
                    except (json.JSONDecodeError, AttributeError):
                        pass
                if duedate is None and isinstance(customdata_raw, dict):
                    duedate = customdata_raw.get("duedate")

                result.append(
                    Deadline(
                        id=instance_id,
                        course_id=course_id,
                        module_id=cmid,
                        instance_id=instance_id,
                        name=module.get("name", ""),
                        modname="assign",
                        due_date=self._from_unix(duedate),
                        allow_submissions_from=None,
                        cutoff_date=None,
                        url=self._module_url(cmid) if cmid else None,
                        raw=module,
                    )
                )
        return result

    async def get_course_deadlines(self, course_id: int) -> List[Deadline]:
        """Return all deadlines for a single course."""
        return await self.get_assignments(course_id=course_id)

    async def get_course_grades(
        self,
        course_id: int,
        user_id: Optional[int] = None,
    ) -> List[UserCourseProgress]:
        """Return grade items per user for a course.

        If user_id is omitted the LMS returns all participants the token can see.
        """
        params: Dict[str, Any] = {"courseid": course_id}
        if user_id is not None:
            params["userid"] = user_id

        raw = await self._call("gradereport_user_get_grade_items", params=params)
        if not isinstance(raw, dict):
            raise LMSResponseError("Unexpected response shape for gradereport_user_get_grade_items")

        result: List[UserCourseProgress] = []
        for user_grade in raw.get("usergrades", []):
            grade_items: List[GradeItem] = []
            for item in user_grade.get("gradeitems", []):
                submitted_at = None
                if item.get("gradedatesubmitted"):
                    submitted_at = self._from_unix(item.get("gradedatesubmitted"))
                graded_at = None
                if item.get("gradedategraded"):
                    graded_at = self._from_unix(item.get("gradedategraded"))

                grade_items.append(
                    GradeItem(
                        id=item.get("id"),
                        name=item.get("itemname", ""),
                        item_type=item.get("itemtype", ""),
                        item_module=item.get("itemmodule"),
                        item_instance=item.get("iteminstance"),
                        category_id=item.get("categoryid"),
                        cmid=item.get("cmid"),
                        grade_raw=item.get("graderaw"),
                        grade_max=item.get("grademax"),
                        grade_min=item.get("grademin"),
                        grade_formatted=item.get("gradeformatted"),
                        feedback=item.get("feedback") or None,
                        submitted_at=submitted_at,
                        graded_at=graded_at,
                        raw=item,
                    )
                )

            result.append(
                UserCourseProgress(
                    user_id=user_grade.get("userid"),
                    course_id=user_grade.get("courseid"),
                    user_fullname=user_grade.get("userfullname"),
                    grade_items=grade_items,
                    raw=user_grade,
                )
            )
        return result

    async def get_user_course_progress(
        self,
        course_id: int,
        user_id: int,
    ) -> UserCourseProgress:
        """Return the progress of a specific user in a specific course."""
        grades = await self.get_course_grades(course_id=course_id, user_id=user_id)
        if not grades:
            return UserCourseProgress(
                user_id=user_id,
                course_id=course_id,
                completion_status="no_data",
                grade_items=[],
            )

        progress = grades[0]
        progress.completion_status = "in_progress"

        # Try to enrich completion status via activity completion API if available.
        try:
            completion = await self._call(
                "core_completion_get_activities_completion_status",
                params={"courseid": course_id, "userid": user_id},
            )
            statuses = completion.get("statuses", [])
            if statuses:
                completed = sum(1 for s in statuses if s.get("state"))
                total = len(statuses)
                progress.completion_status = (
                    "completed" if total > 0 and completed == total else "in_progress"
                )
        except LMSResponseError:
            # Completion criteria may not be configured; leave as in_progress.
            pass

        # Compute a simple overall grade from assignment grade items.
        assignments = [gi for gi in progress.grade_items if gi.item_module == "assign"]
        graded = [gi for gi in assignments if gi.grade_raw is not None]
        if graded:
            progress.overall_grade = round(
                sum(gi.grade_raw or 0 for gi in graded) / len(graded), 2
            )
            progress.overall_grade_max = 100.0
            progress.overall_grade_formatted = f"{progress.overall_grade:.0f}%"
        elif assignments:
            progress.overall_grade_formatted = "-"

        return progress


# Singleton adapter instance used by the application.
lms_adapter = MoodleLMSAdapter()
