"""Canonical Pydantic models for LMS data consumed by AI Curator."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Course(BaseModel):
    """Canonical representation of a course in LMS."""

    id: int
    shortname: str
    fullname: str
    displayname: Optional[str] = None
    summary: Optional[str] = None
    visible: bool = True
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    url: Optional[str] = None
    raw: Optional[Dict[str, Any]] = Field(None, exclude=True)


class CourseModule(BaseModel):
    """A module (activity/resource) inside a course section."""

    id: int
    instance_id: int
    name: str
    modname: str
    section_id: int
    section_name: Optional[str] = None
    section_number: Optional[int] = None
    visible: bool = True
    url: Optional[str] = None
    contents: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    raw: Optional[Dict[str, Any]] = Field(None, exclude=True)


class Deadline(BaseModel):
    """A course deadline derived from an assignment or other activity."""

    id: int
    course_id: int
    module_id: int
    instance_id: int
    name: str
    modname: str = "assign"
    due_date: Optional[datetime] = None
    allow_submissions_from: Optional[datetime] = None
    cutoff_date: Optional[datetime] = None
    url: Optional[str] = None
    raw: Optional[Dict[str, Any]] = Field(None, exclude=True)


class GradeItem(BaseModel):
    """A single grade item for a user in a course."""

    id: int
    name: Optional[str] = ""
    item_type: str
    item_module: Optional[str] = None
    item_instance: Optional[int] = None
    category_id: Optional[int] = None
    cmid: Optional[int] = None
    grade_raw: Optional[float] = None
    grade_max: Optional[float] = None
    grade_min: Optional[float] = None
    grade_formatted: Optional[str] = None
    feedback: Optional[str] = None
    submitted_at: Optional[datetime] = None
    graded_at: Optional[datetime] = None
    raw: Optional[Dict[str, Any]] = Field(None, exclude=True)


class UserCourseProgress(BaseModel):
    """Aggregated progress for a user in a course."""

    user_id: int
    course_id: int
    user_fullname: Optional[str] = None
    completion_status: Optional[str] = None
    grade_items: List[GradeItem] = Field(default_factory=list)
    overall_grade: Optional[float] = None
    overall_grade_max: Optional[float] = None
    overall_grade_formatted: Optional[str] = None
    raw: Optional[Dict[str, Any]] = Field(None, exclude=True)


class LMSHealth(BaseModel):
    """LMS connectivity check result."""

    status: str
    detail: Optional[str] = None
    response_time_ms: Optional[float] = None
