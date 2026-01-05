from rest_framework import serializers
from django.db import transaction
from .models import Exam, Question, Choice, Submission, Answer
import django.utils.timezone as timezone
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from datetime import timedelta
import uuid
from .utils.helper import normalize_text
from rest_framework import serializers
from django.contrib.auth import get_user_model


User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists")
        return value
    

    def validate_email(self, value):
        validate_email(value)
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email already exists")
        return value.lower()
    

    def validate_password(self, value):
        validate_password(value)  # should already be validated in the UI, but in case
        return value


    def create(self, validated_data):
        """
        Create an inactive user and an EmailVerification token.
        Registration will require the user to verify their email before logging in.
        """
        email = validated_data['email'].lower()
        user = User.objects.create_user(
            username=validated_data['username'],
            email=email,
            password=validated_data['password'],
            is_active=False  # require email verification
        )

        # create verification token record (expires in 48 hours)
        from .models import EmailVerification
        expires_at = timezone.now() + timedelta(hours=48)
        ev = EmailVerification.objects.create(user=user, token=uuid.uuid4(), expires_at=expires_at)
        return {'user': user, 'verification_token': str(ev.token)}
    


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class LoginResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    expires_in_hours = serializers.IntegerField()



class ExamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "course",
            "duration",
            "metadata",
            "start_at",
            "end_at",
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        title = attrs.get("title")
        course = attrs.get("course")

        exists = Exam.objects.filter(
            created_by=user,
            title__iexact=title,
            course__iexact=course,
        ).exists()

        if exists:
            raise serializers.ValidationError(
                "An exam with this title already exists for this course."
            )

        return attrs

    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)



    # def create(self, validated_data):
    #     user = self.context["request"].user
    #     exam, created = Exam.objects.get_or_create(
    #         created_by=user,
    #         title=validated_data["title"],
    #         course=validated_data["course"],
    #         defaults=validated_data,
    #     )
    #     return exam







class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["text", "is_correct"]



class QuestionBulkSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            "text",
            "type",
            "reference_answer",
            "max_score",
            "metadata",
            "choices",
        ]

    def validate(self, attrs):
        q_type = attrs.get("type")
        choices = attrs.get("choices", [])

                # MCQ rules
        if q_type == Question.Types.MCQ:
            if not choices:
                raise serializers.ValidationError("MCQ questions must have choices.")
            if not any(c.get("is_correct") for c in choices):
                raise serializers.ValidationError("MCQ must have at least one correct choice.")

        # Non-MCQ rules
        if q_type != Question.Types.MCQ and choices:
            raise serializers.ValidationError("Only MCQ questions can have choices.")

        return attrs
    




class BulkQuestionCreateSerializer(serializers.Serializer):
    questions = QuestionBulkSerializer(many=True)

    def create(self, validated_data):
        exam = self.context["exam"]
        questions_data = validated_data["questions"]

        # Existing questions map
        existing = {
            (q.type, normalize_text(q.text))
            for q in Question.objects.filter(exam=exam)
        }

        created_questions = []
        choice_objects = []

        for q in questions_data:
            key = (q["type"], normalize_text(q["text"]))

            if key in existing:
                continue  # skip duplicate

            choices = q.pop("choices", [])
            question = Question.objects.create(exam=exam, **q)
            created_questions.append(question)
            existing.add(key)

            for choice in choices:
                choice_objects.append(
                    Choice(question=question, **choice)
                )

        Choice.objects.bulk_create(choice_objects)

        return {
            "created": len(created_questions),
            "skipped": len(questions_data) - len(created_questions),
        }





class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "type",
            "reference_answer",
            "max_score",
            "metadata",
            "choices",
            "created_at",
        ]

    def validate(self, attrs):
        q_type = attrs.get("type", self.instance.type if self.instance else None)
        choices = attrs.get("choices", [])

        if q_type == Question.Types.MCQ:
            if not choices:
                raise serializers.ValidationError(
                    "MCQ questions must have choices."
                )
            if not any(c.get("is_correct") for c in choices):
                raise serializers.ValidationError(
                    "At least one choice must be marked as correct."
                )

        return attrs
    
    




class AnswerCreateSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_choice_id = serializers.IntegerField(required=False, allow_null=True)
    answer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)



class SubmissionCreateSerializer(serializers.Serializer):
    started_at = serializers.DateTimeField(required=False)
    answers = AnswerCreateSerializer(many=True)

    def validate(self, data):
        request = self.context['request']
        exam_id = self.context['exam_id']  # passed from view
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            raise serializers.ValidationError("Exam does not exist.")

        # check exam availability
        now = timezone.now()
        if exam.start_at and exam.start_at > now:
            raise serializers.ValidationError("Exam not yet available.")
        if exam.end_at and exam.end_at < now:
            raise serializers.ValidationError("Exam has ended.")
    

        # check duplicate submission
        student = request.user
        if Submission.objects.filter(student=student, exam=exam).exists():
            raise serializers.ValidationError("This exam has already been submitted and graded.")

        question_ids = [q['question_id'] for q in data['answers']]
        # ensure all question ids belong to the exam
        qs_count = Question.objects.filter(exam=exam, id__in=question_ids).count()
        if qs_count != len(set(question_ids)):
            raise serializers.ValidationError("One or more questions invalid for this exam.")

        # validate choices
        for ans in data['answers']:
            choice_id = ans.get('selected_choice_id')
            if choice_id:
                if not Choice.objects.filter(pk=choice_id, question_id=ans['question_id']).exists():
                    raise serializers.ValidationError(f"Choice {choice_id} not valid for question {ans['question_id']}")

        # attach exam for create
        self.context['exam'] = exam
        return data
    


    def create(self, validated_data):
        request = self.context['request']
        exam = self.context['exam']
        student = request.user

        with transaction.atomic():
            submission = Submission.objects.create(
                student=student,
                exam=exam,
                started_at=validated_data.get('started_at'),
                status=Submission.Status.PENDING
            )

            answers_bulk = []
            for ans in validated_data['answers']:
                answer = Answer(
                    submission=submission,
                    question_id=ans['question_id'],
                    answer_text=ans.get('answer_text'),
                    selected_choice_id=ans.get('selected_choice_id')
                )
                answers_bulk.append(answer)
            Answer.objects.bulk_create(answers_bulk)
            
            # trigger grading
            from .services import grade_submission
            grade_result = grade_submission(submission.id)
            submission_id = submission.id
            # grade_result is dict with overall_score, per_question
            submission.score = grade_result.get('score')
            submission.grading_details = grade_result
            submission.status = Submission.Status.GRADED
            submission.graded_at = timezone.now()
            submission.save(update_fields=['score', 'grading_details', 'status', 'graded_at'])

            data = {
                'submission_id': submission_id,
                "message": "Exam submitted and graded successfully",
                'exam_id': exam.id,
                'student_id': student.id,
                'submitted_at': submission.submitted_at,
                'score': submission.score,
                'max_score': round(grade_result.get('max_score', 0), 2),
                'overall_score': f'{submission.score} / {round(grade_result.get("max_score", 0), 2)}',
                **submission.grading_details,
            }

            return data





class ExamPlayChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]


class ExamPlayQuestionSerializer(serializers.ModelSerializer):
    choices = ExamPlayChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "type",
            "max_score",
            "choices",
        ]




class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ["id", "text"]



class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "text",
            "type",
            "max_score",
            "metadata",
            "choices",
        ]


class ExamDetailsSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "course",
            "duration",
            "metadata",
            "start_at",
            "end_at",
            "questions",
        ]



class ExamListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            "id",
            "title",
            "course",
            "duration",
            "start_at",
            "end_at",
            "created_at",
        ]