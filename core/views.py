from django.db import connection
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthcheckView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_ok = False

        payload = {
            "status": "ok" if db_ok else "degraded",
            "database": "ok" if db_ok else "error",
            "timestamp": timezone.now().isoformat(),
        }
        status_code = 200 if db_ok else 503
        return Response(payload, status=status_code)
