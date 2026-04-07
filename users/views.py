from django.contrib.auth import get_user_model
from rest_framework import viewsets

from users.permissions import IsSuperAdmin
from users.serializers import UserCreateSerializer, UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    permission_classes = [IsSuperAdmin]

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return UserCreateSerializer
        return UserSerializer
