from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from settings_app.models import Bar, BarSession, SystemConfiguration
from settings_app.serializers import BarSerializer, BarSessionSerializer, SystemConfigurationSerializer
from settings_app.services import close_bar_session, open_bar_session
from users.permissions import IsSupervisorOrAbove


class SystemConfigurationViewSet(viewsets.ModelViewSet):
    queryset = SystemConfiguration.objects.all().order_by("id")
    serializer_class = SystemConfigurationSerializer
    permission_classes = [IsSupervisorOrAbove]


class BarViewSet(viewsets.ModelViewSet):
    queryset = Bar.objects.all().order_by("id")
    serializer_class = BarSerializer
    permission_classes = [IsSupervisorOrAbove]


class BarSessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = BarSession.objects.select_related("bar", "opened_by", "closed_by").all()
    serializer_class = BarSessionSerializer
    permission_classes = [IsSupervisorOrAbove]

    @action(methods=["post"], detail=False)
    def open(self, request):
        bar_id = request.data.get("bar_id")
        if not bar_id:
            return Response({"detail": "bar_id es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        bar = Bar.objects.filter(id=bar_id, is_active=True).first()
        if not bar:
            return Response({"detail": "Barra no encontrada o inactiva"}, status=status.HTTP_404_NOT_FOUND)

        if BarSession.objects.filter(bar=bar, is_open=True).exists():
            return Response({"detail": "La barra ya tiene una sesion abierta"}, status=status.HTTP_400_BAD_REQUEST)

        session = open_bar_session(bar=bar, user=request.user)
        return Response(self.get_serializer(session).data, status=status.HTTP_201_CREATED)

    @action(methods=["post"], detail=True)
    def close(self, request, pk=None):
        session = self.get_object()
        if not session.is_open:
            return Response({"detail": "La sesion ya esta cerrada"}, status=status.HTTP_400_BAD_REQUEST)
        session = close_bar_session(session=session, user=request.user)
        return Response(self.get_serializer(session).data)
