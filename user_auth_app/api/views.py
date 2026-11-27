from django.db import transaction
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny

from .serializers import RegistrationSerializer


class RegistrationView(CreateAPIView):
    """Create a user without requiring an authentication token."""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Keep uniqueness checks and the insert in one SQLite transaction."""
        return super().create(request, *args, **kwargs)
