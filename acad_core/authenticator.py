from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class CustomTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token.')

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted.')

        expiry_hours = getattr(settings, 'TOKEN_EXPIRE_HOURS', 24)

        if token.created + timedelta(hours=expiry_hours) < timezone.now():
            token.delete()
            raise exceptions.AuthenticationFailed('Token expired.')

        return (token.user, token)
