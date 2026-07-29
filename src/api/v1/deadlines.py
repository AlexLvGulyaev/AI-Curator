"""API endpoints for course deadlines from LMS."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from adapters.lms_adapter import MoodleLMSAdapter, lms_adapter
from schemas.lms import Deadline

router = APIRouter(prefix="/courses", tags=["deadlines"])


def get_lms_adapter() -> MoodleLMSAdapter:
    """Dependency factory for the LMS adapter."""
    return lms_adapter


@router.get("/{course_id}/deadlines", response_model=List[Deadline])
async def list_course_deadlines(
    course_id: int,
    adapter: MoodleLMSAdapter = Depends(get_lms_adapter),
):
    """Return all assignment deadlines for the given course."""
    try:
        return await adapter.get_course_deadlines(course_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch deadlines from LMS: {exc}",
        ) from exc
