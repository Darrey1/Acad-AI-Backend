from django.conf import settings

def _get_backend():
    # backend = getattr(settings, 'GRADER_BACKEND', 'mock')
    # return backend
    return "mock" # for now, only mock is implemented

def grade_submission(submission_id):
    from .grader import MockGrader, LLMGrader
    from ..models import Submission
    submission = Submission.objects.get(pk=submission_id)
    backend = _get_backend()
    if backend == 'mock':
        grader = MockGrader()
    elif backend == 'llm':
        grader = LLMGrader()
    else:
        grader = MockGrader()
    return grader.grade_submission(submission)