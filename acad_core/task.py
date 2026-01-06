import asyncio
from .services import grade_submission


def grade_submission_async(submission_id: int):
    """
    Background grading task.
    Runs in a separate thread.
    Celery or other task queues can be used in production.  
    """
    grade_submission(submission_id)


