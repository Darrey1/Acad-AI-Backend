# assessments/services/grader.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from ..models import Submission, Answer, Question, Choice
from django.db import transaction
from django.conf import settings
import math
import re
from collections import Counter
from django.utils import timezone


# utility tokenizer
def tokenize(text: str):
    if not text:
        return []
    # lowercase and split on non-word
    return [t for t in re.findall(r'\w+', text.lower()) if len(t) > 1]



class BaseGrader(ABC):
    name = 'base'
    version = '0.0'

    @abstractmethod
    def grade_submission(self, submission: Submission) -> Dict[str, Any]:
        pass



class MockGrader(BaseGrader):
    name = 'mock'
    version = '1.0'

    def _score_mcq(self, answer: Answer, question: Question):
        if answer.selected_choice_id is None:
            return 0.0, "No choice selected"
        # rely on Choice.is_correct
        if answer.selected_choice and answer.selected_choice.is_correct:
            return float(question.max_score), "Correct"
        return 0.0, "Incorrect"



    def _score_short_or_essay(self, answer: Answer, question: Question):
        # simple token-overlap cosine similarity between student answer and reference_answer
        ref = question.reference_answer or ""
        student = answer.answer_text or ""
        ref_tokens = tokenize(ref)
        student_tokens = tokenize(student)
        if not ref_tokens or not student_tokens:
            return 0.0, "No content to compare"

        ref_counts = Counter(ref_tokens)
        stu_counts = Counter(student_tokens)

        # compute cosine similarity
        all_terms = set(ref_counts) | set(stu_counts)
        dot = sum(ref_counts[t] * stu_counts.get(t, 0) for t in all_terms)
        ref_norm = math.sqrt(sum(v*v for v in ref_counts.values()))
        stu_norm = math.sqrt(sum(v*v for v in stu_counts.values()))
        if ref_norm == 0 or stu_norm == 0:
            sim = 0.0
        else:
            sim = dot / (ref_norm * stu_norm)
        score = float(sim) * float(question.max_score)
        feedback = f"Similarity {sim:.2f}"
        return round(score, 2), feedback



    def grade_submission(self, submission: Submission):
        # fetch submission with answers and related questions & choices
        submission = Submission.objects.select_related('exam', 'student').prefetch_related('answers__question', 'answers__selected_choice').get(pk=submission.pk)
        total = 0.0
        max_score = sum(float(ans.question.max_score) for ans in submission.answers.all())
        per_question = []
        with transaction.atomic():
            for ans in submission.answers.all():
                q = ans.question

                if q.type == Question.Types.MCQ:
                    score, fb = self._score_mcq(ans, q)
                else:
                    score, fb = self._score_short_or_essay(ans, q)
                # persist per-answer score & feedback
                ans.score = score
                ans.feedback = {'feedback_text': fb}
                ans.save(update_fields=['score', 'feedback'])
                total += score
                per_question.append({
                    'question_id': q.id,
                    'score': score,
                    'max_score': float(q.max_score),
                    'feedback': fb
                })

            # update submission
            submission.score = round(total, 2)
            submission.status = Submission.Status.GRADED
            submission.graded_at = timezone.now()
            submission.grading_details = {
                'score': submission.score,
                'max_score': round(max_score, 2),
                'per_question': per_question,
                'grader': {'name': self.name, 'version': self.version}
            }
            submission.save(update_fields=['score', 'status', 'graded_at', 'grading_details'])

        return submission.grading_details



# LLM adapter 
class LLMGrader(BaseGrader):
    name = 'llm'
    version = '0.1'

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or self._build_client()

    def _build_client(self):
        # build a client using openai 
        return None

    def grade_submission(self, submission: Submission):
        """
        Example implementation:
        - Prepare prompt with question reference answers and student answers
        - Call LLM with a system prompt instructing to return structured JSON with per-question scores
        - Parse and persist result
        Note: real implementation must be robust against LLM hallucinations and timeouts.
        """
        # Pseudocode - keep synchronous for now; for production prefer asynchronous processing / background task
        # 1) Gather inputs
        # 2) Prepare prompt
        # 3) Call LLM
        # 4) Parse JSON response
        # 5) Persist scores & feedback
        raise NotImplementedError("LLMGrader is an adapter skeleton. please continue with mock implementation...")