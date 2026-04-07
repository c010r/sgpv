from django.contrib.auth import authenticate
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import AuditLog
from users.auth_serializers import LoginSerializer, LogoutSerializer


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = authenticate(request, username=data["username"], password=data["password"])
        ip = request.META.get("REMOTE_ADDR", "")

        if not user:
            return Response({"detail": "Credenciales invalidas"}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            AuditLog.objects.create(
                action="LOGIN_FAILED",
                model_name="Auth",
                object_id=str(user.id),
                actor=user,
                metadata={"reason": "inactive_user", "ip": ip},
            )
            return Response({"detail": "Usuario inactivo"}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        AuditLog.objects.create(
            action="LOGIN",
            model_name="Auth",
            object_id=str(user.id),
            actor=user,
            metadata={"ip": ip},
        )
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip = request.META.get("REMOTE_ADDR", "")
        AuditLog.objects.create(
            action="LOGOUT",
            model_name="Auth",
            object_id=str(request.user.id),
            actor=request.user,
            metadata={"ip": ip},
        )

        return Response({"detail": "Logout registrado"}, status=status.HTTP_200_OK)
