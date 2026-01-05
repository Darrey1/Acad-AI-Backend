from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterAPIView,
    LoginAPIView,
    VerifyEmailAPIView,
    ExamViewSet,
    AdminExamViewSet
)

router = DefaultRouter()

router.register(r"admin/exams", AdminExamViewSet, basename="admin-exam")
router.register(r"user/exams", ExamViewSet, basename="user-exam")



urlpatterns = [
    path('auth/register/', RegisterAPIView.as_view(), name='api_register'),
    path('auth/login/', LoginAPIView.as_view(), name='api_login'),
    path(
        'auth/verify-email/', 
        VerifyEmailAPIView.as_view(), 
        name='api_verify_email'
    ),
]

urlpatterns += router.urls
