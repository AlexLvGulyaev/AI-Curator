"""API endpoints for the current student's progress."""

from fastapi import APIRouter, Depends, HTTPException, status

from adapters.lms_adapter import MoodleLMSAdapter, lms_adapter
from schemas.lms import UserCourseProgress

router = APIRouter(prefix="/me", tags=["progress"])

# In Day 3 authentication is not implemented yet. The current user is hard-coded
# to the test student account created in Moodle.
CURRENT_STUDENT_ID = 3
CURRENT_COURSE_ID = 3


def get_lms_adapter() -> MoodleLMSAdapter:
    """Dependency factory for the LMS adapter."""
    return lms_adapter


@router.get("/progress", response_model=UserCourseProgress)
async def get_my_progress(
    adapter: MoodleLMSAdapter = Depends(get_lms_adapter),
):
    """Return the learning progress of the current student in the demo course.

    This is a placeholder implementation for Day 3. Real authentication will be
    added in a later sprint.
    """
    try:
        return await adapter.get_user_course_progress(
            course_id=CURRENT_COURSE_ID,
            user_id=CURRENT_STUDENT_ID,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch progress from LMS: {exc}",
        ) from exc
