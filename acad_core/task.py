import asyncio
from .services import grade_submission


# Run grading in an asynchronous manner (Celery or other task queues can be used in production)
async def grade_submission_async(submission_id: int):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, grade_submission, submission_id)


