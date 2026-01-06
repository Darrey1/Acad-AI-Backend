import asyncio
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView
from rest_framework.viewsets import ViewSet
from django.db.models.functions import Upper, Replace
from rest_framework.response import Response
from django.db.models import Value
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from django.utils import timezone
from django.http import HttpResponse
from django.utils.html import escape
from rest_framework.permissions import IsAuthenticated
from .models import Exam, Submission, EmailVerification, Question, Choice, Answer
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.throttling import ScopedRateThrottle
from django.conf import settings
from .serializers import (
    SubmissionCreateSerializer, 
    RegisterSerializer,
    ExamCreateSerializer,
    BulkQuestionCreateSerializer,
    QuestionSerializer,
    ExamDetailsSerializer,
    ExamListSerializer,
    LoginSerializer,
    LoginResponseSerializer,
)
from drf_spectacular.utils import extend_schema


User = get_user_model()




############################### AUTH VIEWS #######################################

class RegisterAPIView(GenericAPIView):
    """
    User registration API view.
    """
    serializer_class = RegisterSerializer
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_register"

    @extend_schema(
        request=RegisterSerializer,
        responses={
            201: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "user_id": {"type": "integer"},
                },
            }
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()
        user = result["user"]
        verification_token = result["verification_token"]

        verification_link = (
            f"{request.scheme}://{request.get_host()}"
            f"/api/auth/verify-email?token={verification_token}"
        )

        # In production, send the verification link via email.

        return Response(
            {
                "message": "User created. copy the verification link below and paste it in your browser to verify your email.",
                "user_id": user.id,
                "developer_note": "In a production environment, the verification link would be sent via email.",
                "verification_link": verification_link,
            },
            status=status.HTTP_201_CREATED,
        )




@extend_schema(exclude=True)
class VerifyEmailAPIView(APIView):
    """
    Email verification via link (GET).
    """
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_verify"

    def get(self, request, *args, **kwargs):
        token = request.query_params.get("token")

        if not token:
            return self._render_html(
                title="Verification Failed",
                message="Verification token is missing.",
                success=False,
            )

        try:
            ev = EmailVerification.objects.get(token=token)
        except EmailVerification.DoesNotExist:
            return self._render_html(
                title="Verification Failed",
                message="Invalid or already used verification token.",
                success=False,
            )

        if ev.is_expired():
            ev.delete()
            return self._render_html(
                title="Verification Failed",
                message="This verification link has expired.",
                success=False,
            )

        user = ev.user
        user.is_active = True
        user.save(update_fields=["is_active"])
        ev.delete()

        return self._render_html(
            title="Email Verified 🎉",
            message="Your email has been successfully verified. You can now log in.",
            success=True,
        )

    def _render_html(self, title: str, message: str, success: bool):
        color = "#16a34a" if success else "#dc2626"

        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <title>{escape(title)}</title>
            <style>
                body {{
                    font-family: system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
                    background-color: #f9fafb;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    height: 100vh;
                }}
                .card {{
                    background: #ffffff;
                    padding: 2rem 2.5rem;
                    border-radius: 10px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.08);
                    max-width: 420px;
                    text-align: center;
                }}
                h1 {{
                    color: {color};
                    margin-bottom: 0.75rem;
                }}
                p {{
                    color: #374151;
                    font-size: 1rem;
                    line-height: 1.5;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h1>{escape(title)}</h1>
                <p>{escape(message)}</p>
            </div>
        </body>
        </html>
        """

        return HttpResponse(html, content_type="text/html")







class LoginAPIView(GenericAPIView):
    """
    Login API view.

    Login using email and password.
    Returns a Bearer token that expires after 24 hours.
    """

    serializer_class = LoginSerializer
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_login"

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: LoginResponseSerializer,
            400: {"description": "Email and password are required"},
            401: {"description": "Invalid credentials"},
            403: {"description": "Account inactive or email not verified"},
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"].lower()
        password = serializer.validated_data["password"]

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.is_active:
            return Response(
                {"detail": "Email not verified or account inactive"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Rotate token
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response(
            {
                "token": token.key,
                "expires_in_hours": getattr(settings, "TOKEN_EXPIRE_HOURS", 24),
            },
            status=status.HTTP_200_OK,
        )








############################### ADMIN VIEWS #######################################


class AdminExamViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Exams by Admins. \n
    Admins can create, update, delete, and list exams. \n
    They can also bulk upload questions to an exam and manage individual questions.
    """
    serializer_class = ExamCreateSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action == "bulk_upload_questions":
            return BulkQuestionCreateSerializer
        if self.action in [
            "list_questions",
            "question_detail"
        ]:
            return QuestionSerializer
        
        return self.serializer_class

    def get_queryset(self):
        """ Retrieve exams created by the admin user. """
        # Admins can only manage exams they created
        return Exam.objects.filter(created_by=self.request.user)
    

    def perform_create(self, serializer):
        """ 
        Create exam with the current user as creator.
        
        """
        try:
            serializer.save(created_by=self.request.user)
        except IntegrityError:
            raise ValidationError({"detail": "This exam already exists."})



    @action(
        detail=True,
        methods=["post"],
        url_path="upload-questions"
    )
    @transaction.atomic
    def bulk_upload_questions(self, request, pk=None):
        """
        Bulk upload questions to this exam.\n
        Note: \n
        reference_answer is required for SHORT and ESSAY question types. \n
        But for MCQ type, choices must be provided with one marked as correct. \n\n
        Example request data: \n
             { \n
            "type": "MCQ",\n
            "text": "Your question text here",\n
            "reference_answer": "", # Not required for MCQ \n
            "max_score": 1.0, \n
            "metadata": {"difficulty": "easy"}, \n
            "choices": [ \n
                {"text": "Option 1", "is_correct": false},\n
                {"text": "Option 2", "is_correct": true},\n
                {"text": "Option 3", "is_correct": false},\n
                {"text": "Option 4", "is_correct": false}\n
            ]} \n
        """
        exam = get_object_or_404(Exam, id=pk)

        if exam.created_by != request.user:
            return Response(
                {"detail": "You do not have permission to modify this exam."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer_class = self.get_serializer_class()

        serializer = serializer_class(
            data=request.data,
            context={"exam": exam},
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        return Response(
            {
                "message": "Questions uploaded successfully",
                "created": result.get("created", 0),
                "skipped_duplicates": result.get("skipped", 0),
            },
            status=status.HTTP_201_CREATED,
        )


    # -----------------------------------
    # LIST QUESTIONS FOR AN EXAM
    # -----------------------------------
    @action(
        detail=True,
        methods=["get"],
        url_path="questions",
    )
    def list_questions(self, request, pk=None):
        """
        List all questions under this exam. \n 
        """
        exam = get_object_or_404(Exam, id=pk, created_by=request.user)

        questions = Question.objects.filter(exam=exam).prefetch_related("choices")
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(questions, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    


    @action(
    detail=True,
    methods=["get", "put", "delete"],
    url_path="questions/(?P<question_id>[^/.]+)",
)
    @transaction.atomic
    def question_detail(self, request, pk=None, question_id=None):
        """
        Retrieve, update or delete a specific question for an exam.
        """
        exam = get_object_or_404(Exam, id=pk, created_by=request.user)
        question = get_object_or_404(Question, id=question_id, exam=exam)
        serializer_class = self.get_serializer_class()

        # -----------------------
        # RETRIEVE
        # -----------------------
        if request.method == "GET":
            serializer = serializer_class(question)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # -----------------------
        # UPDATE
        # -----------------------
        if request.method == "PUT":
            serializer = serializer_class(
                question,
                data=request.data,
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            if question.type == Question.Types.MCQ:
                Choice.objects.filter(question=question).delete()
                choices = request.data.get("choices", [])
                Choice.objects.bulk_create(
                    [Choice(question=question, **c) for c in choices]
                )

            return Response(
                {"message": "Question updated successfully"},
                status=status.HTTP_200_OK,
            )

        # -----------------------
        # DELETE
        # -----------------------
        if request.method == "DELETE":
            question.delete()
            return Response(
                {"message": "Question deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )







############################### STUDENT VIEWS #######################################


class ExamViewSet(ViewSet):
    """
    ViewSet for managing Exams. \n
    Students can list available exams and retrieve exam details. \n
    They can also start and submit exams.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "submit":
            return SubmissionCreateSerializer
        return None 

    # List all available exams
    def list(self, request):
        """
        API view to list all currently available exams.
        
        """
        now = timezone.now()

        exams = Exam.objects.filter(
            start_at__lte=now,
            end_at__gte=now
        ).order_by("-created_at")

        if not exams.exists():
            return Response(
                {"detail": "No exams are currently available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ExamListSerializer(exams, many=True)
        return Response(serializer.data)



    # Exam details
    def retrieve(self, request, pk=None):
        """
        API view to retrieve details of a specific exam.
        """
        exam = get_object_or_404(Exam, id=pk)

        serializer = ExamDetailsSerializer(exam)
        data = serializer.data.copy()
        data.pop("questions", None)

        data.update({
            "total_questions": exam.questions.count(),
            "message": f"{exam.course.upper()} exam details retrieved successfully.",
            "developer_note": "Questions are not included, Send POST request to start endpoint to begin the exam."
        })

        return Response(data)
    


    @action(detail=True, methods=["get"], url_path="results", url_name="exam-results")
    def results(self, request, pk=None):
        """
        Retrieve the authenticated student's result for a given exam.
        """
        submission = get_object_or_404(
            Submission,
            exam_id=pk,
            student=request.user
        )

        # grading still in progress
        if submission.status != Submission.Status.GRADED:
            return Response(
                {
                    "submission_id": submission.id,
                    "exam_id": submission.exam_id,
                    "status": submission.status,
                    "message": "Grading in progress. Please check back shortly."
                },
                status=status.HTTP_202_ACCEPTED
            )

        # grading completed
        return Response(
            {
                "submission_id": submission.id,
                "exam_id": submission.exam_id,
                "student_id": submission.student_id,
                "status": submission.status,
                "submitted_at": submission.submitted_at,
                "graded_at": submission.graded_at,
                "score": submission.score,
                "max_score": submission.grading_details.get("max_score"),
                "grading_details": submission.grading_details,
                "answers": [
                    {
                        "question_id": ans.question_id,
                        "selected_choice_id": ans.selected_choice_id,
                        "answer_text": ans.answer_text,
                        "score": ans.score,
                        "feedback": ans.feedback,
                    }
                    for ans in submission.answers.all()
                ],
            },
            status=status.HTTP_200_OK
        )

    

    # Start exam
    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        """
        API view to start an exam for a student.

        """
        exam = get_object_or_404(
            Exam.objects.prefetch_related("questions__choices"),
            id=pk
        )

        submission, _ = Submission.objects.get_or_create(
            student=request.user,
            exam=exam,
            status=Submission.Status.PENDING,
            defaults={"started_at": timezone.now()}
        )

        serializer = ExamDetailsSerializer(exam)

        return Response({
            "submission_id": submission.id,
            "message": "Exam started. Proceed to answer questions.",
            "total_questions": exam.questions.count(),
            "questions": serializer.data.get("questions", [])
        })


    # Submit exam
    @action(detail=True, methods=["post"], url_path="submit" )
    def submit(self, request, pk=None):
        """
        Api view to submit an exam for grading. \n
        Request data should include answers to the exam questions. \n
        Example request data: \n
            { \n
            "answers": [ \n
                { \n
                    "question_id": 1, \n
                    "selected_choice_id": 3, # for MCQ type \n
                    "answer_text": "Your answer text here" # for SHORT and ESSAY types leave it blank for MCQ \n
                }, \n
                ... \n
            ] }\n
        """

            # Get the serializer class for this action
        serializer_class = self.get_serializer_class()

        serializer = serializer_class(
            data=request.data,
            context={
                "request": request,
                "exam_id": pk
            }
        )
        serializer.is_valid(raise_exception=True)
        submission = serializer.save()
        print("Submission saved, triggering async grading...", submission.id, submission.status)

        # async grading trigger
        from .task import grade_submission_async
        asyncio.create_task(grade_submission_async(submission.id))

        return Response({
            "submission_id": submission.id,
            "status": submission.status,
            "message": "Exam submitted. Grading in progress."
        }, status=status.HTTP_201_CREATED)





