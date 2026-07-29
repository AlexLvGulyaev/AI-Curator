"""API endpoints for course data from LMS."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from adapters.lms_adapter import MoodleLMSAdapter, lms_adapter
from schemas.lms import Course

router = APIRouter(prefix="/courses", tags=["courses"])


def get_lms_adapter() -> MoodleLMSAdapter:
    """Dependency factory for the LMS adapter."""
    return lms_adapter


@router.get("", response_model=List[Course])
async def list_courses(adapter: MoodleLMSAdapter = Depends(get_lms_adapter)):
    """Return the list of courses available in the connected LMS."""
    try:
        return await adapter.get_courses()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch courses from LMS: {exc}",
        ) from exc


@router.get("/{course_id}/contents", response_model=List[dict])
async def get_course_contents(
    course_id: int,
    adapter: MoodleLMSAdapter = Depends(get_lms_adapter),
):
    """Return the content structure (sections and modules) of a course.

    For now returns the raw canonical module list; a dedicated schema will be
    added when the Web UI needs a richer contract.
    """
    try:
        modules = await adapter.get_course_contents(course_id)
        # FastAPI can serialize Pydantic models as dict automatically, but we
        # keep the return type annotation as dict to avoid over-committing.
        return [m.model_dump() for m in modules]
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch course contents from LMS: {exc}",
        ) from exc
