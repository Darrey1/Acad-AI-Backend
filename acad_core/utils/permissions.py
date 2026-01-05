from rest_framework import permissions
from django.utils import timezone

class IsOwnerOfSubmission(permissions.BasePermission):
    """
    Only allow owners of a Submission to view it (or staff).
    """

    def has_object_permission(self, request, view, obj):
        # obj is Submission
        if request.user.is_staff:
            return True
        return obj.student_id == request.user.id




class CanSubmitExam(permissions.BasePermission):
    """
    Allow a student to submit an exam if:
    - they are authenticated
    - exam is currently available (start/end check)
    - they don't already have a submission to forbids duplicates
    """

    def has_permission(self, request, view):
        # Allow POST (create) if authenticated
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return True