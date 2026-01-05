from django.conf import settings
from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
import uuid
from django.utils import timezone

User = settings.AUTH_USER_MODEL


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"EmailVerification(token={self.token}, user_id={self.username})"




class Exam(models.Model):
    title = models.CharField(max_length=255)
    course = models.CharField(max_length=255, db_index=True) 
    duration = models.DurationField(help_text="Exam duration (as interval)", null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)  # instructions
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_exams')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['course']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["created_by", "title", "course"],
                name="unique_exam_per_creator"
            )
        ]
        

    def __str__(self):
        return f"{self.title}_course_{self.course}"
    



class Question(models.Model):
    class Types(models.TextChoices):
        MCQ = "MCQ", "Multiple Choice"
        SHORT = "SHORT", "Short Answer"
        ESSAY = "ESSAY", "Essay"

    exam = models.ForeignKey(Exam, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    type = models.CharField(max_length=10, choices=Types.choices, db_index=True)
    reference_answer = models.TextField(null=True, blank=True)
    max_score = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['exam', 'type']),
            GinIndex(fields=['text'], name='question_text_gin', opclasses=['gin_trgm_ops']), 
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "type", "text"],
                name="unique_exam_question_text"
            )
        ]

    def __str__(self):
        return f"Q{self.pk} ({self.type})"





class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=1024)
    is_correct = models.BooleanField(default=False, db_index=True)

    def __str__(self):
        return f"Choice {self.pk} for Q{self.question_id}"
    




class Submission(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        GRADED = "GRADED", "Graded"
        SUBMITTED = "SUBMITTED", "Submitted"

    student = models.ForeignKey(User, related_name='submissions', on_delete=models.CASCADE, db_index=True)
    exam = models.ForeignKey(Exam, related_name='submissions', on_delete=models.CASCADE, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)
    grading_details = models.JSONField(default=dict, blank=True)  # per-question breakdown, grader metadata

    class Meta:
        # Prevent duplicate submissions by same student to same exam (tunable)
        constraints = [
            models.UniqueConstraint(fields=['student', 'exam'], name='unique_student_exam_submission')
        ]
        indexes = [
            models.Index(fields=['student', 'exam']),
            models.Index(fields=['status', 'graded_at']),
        ]

    def __str__(self):
        return f"Submission {self.pk} by {self.student.username} for {self.exam.title}"
    
    


class Answer(models.Model):
    submission = models.ForeignKey(Submission, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    answer_text = models.TextField(null=True, blank=True)
    score = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    feedback = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['submission', 'question']),
        ]

    def __str__(self):
        return f"Ans {self.pk} for Submission {self.submission_id}"