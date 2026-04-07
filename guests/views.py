import csv
import io

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from guests.models import GuestEntry, GuestImportJob, GuestImportJobError, GuestList
from guests.serializers import GuestCheckinSerializer, GuestEntrySerializer, GuestListSerializer
from users.permissions import IsCajeroOrAbove, IsSupervisorOrAbove


class GuestListViewSet(viewsets.ModelViewSet):
    queryset = GuestList.objects.select_related("created_by").all().order_by("-event_date", "-id")
    serializer_class = GuestListSerializer
    permission_classes = [IsSupervisorOrAbove]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(methods=["post"], detail=True)
    def preview_csv(self, request, pk=None):
        guest_list = self.get_object()
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "Debe enviar archivo CSV en 'file'"}, status=status.HTTP_400_BAD_REQUEST)

        text_data = file_obj.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text_data))
        preview = []
        errors = []
        for idx, row in enumerate(reader, start=2):
            full_name = (row.get("full_name") or "").strip()
            qr_code = (row.get("qr_code") or "").strip()
            document_id = (row.get("document_id") or "").strip()
            if not full_name or not qr_code:
                errors.append(f"Linea {idx}: full_name y qr_code son requeridos")
            preview.append({"line": idx, "full_name": full_name, "qr_code": qr_code, "document_id": document_id})
            if len(preview) >= 100:
                break

        job = GuestImportJob.objects.create(
            guest_list=guest_list,
            status=GuestImportJob.Status.PREVIEWED,
            total_rows=len(preview),
            created_rows=0,
            error_rows=len(errors),
            imported_by=request.user,
        )
        for err in errors:
            GuestImportJobError.objects.create(
                job=job,
                line_number=0,
                message=err,
                raw_data={},
            )

        return Response({"job_id": job.id, "preview_count": len(preview), "preview": preview, "errors": errors})

    @action(methods=["post"], detail=True)
    def import_csv(self, request, pk=None):
        guest_list = self.get_object()
        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"detail": "Debe enviar archivo CSV en 'file'"}, status=status.HTTP_400_BAD_REQUEST)

        text_data = file_obj.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text_data))

        created = 0
        errors = []
        total_rows = 0
        for idx, row in enumerate(reader, start=2):
            total_rows += 1
            full_name = (row.get("full_name") or "").strip()
            qr_code = (row.get("qr_code") or "").strip()
            document_id = (row.get("document_id") or "").strip()
            if not full_name or not qr_code:
                errors.append(f"Linea {idx}: full_name y qr_code son requeridos")
                continue
            _, was_created = GuestEntry.objects.get_or_create(
                guest_list=guest_list,
                full_name=full_name,
                defaults={"qr_code": qr_code, "document_id": document_id},
            )
            if was_created:
                created += 1

        status_value = GuestImportJob.Status.IMPORTED if not errors else GuestImportJob.Status.FAILED
        job = GuestImportJob.objects.create(
            guest_list=guest_list,
            status=status_value,
            total_rows=total_rows,
            created_rows=created,
            error_rows=len(errors),
            imported_by=request.user,
        )
        for error in errors:
            GuestImportJobError.objects.create(job=job, line_number=0, message=error, raw_data={})

        return Response({"job_id": job.id, "created": created, "errors": errors})

    @action(methods=["get"], detail=True)
    def import_jobs(self, request, pk=None):
        guest_list = self.get_object()
        jobs = guest_list.import_jobs.prefetch_related("errors").all().order_by("-id")[:50]
        payload = []
        for job in jobs:
            payload.append(
                {
                    "id": job.id,
                    "status": job.status,
                    "total_rows": job.total_rows,
                    "created_rows": job.created_rows,
                    "error_rows": job.error_rows,
                    "imported_by": job.imported_by.username,
                    "created_at": job.created_at.isoformat(),
                    "errors": [
                        {"line_number": e.line_number, "message": e.message}
                        for e in job.errors.all()[:100]
                    ],
                }
            )
        return Response(payload)

    @action(methods=["get"], detail=True, permission_classes=[IsCajeroOrAbove])
    def occupancy(self, request, pk=None):
        guest_list = self.get_object()
        entries = guest_list.guests.count()
        entered = guest_list.guests.filter(status=GuestEntry.Status.ENTERED).count()
        companions_entered = (
            guest_list.guests.filter(status=GuestEntry.Status.ENTERED).aggregate(total=Sum("companions_used")).get("total")
            or 0
        )
        capacity_used = entered + companions_entered
        return Response(
            {
                "guest_list_id": guest_list.id,
                "entries": entries,
                "entered": entered,
                "companions_entered": companions_entered,
                "capacity_used": capacity_used,
            }
        )


class GuestEntryViewSet(viewsets.ModelViewSet):
    queryset = GuestEntry.objects.select_related("guest_list", "checked_in_by").all().order_by("-id")
    serializer_class = GuestEntrySerializer
    permission_classes = [IsCajeroOrAbove]

    def get_queryset(self):
        queryset = super().get_queryset()
        status_value = self.request.query_params.get("status")
        from_date = self.request.query_params.get("from")
        to_date = self.request.query_params.get("to")
        if status_value:
            queryset = queryset.filter(status=status_value)
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        return queryset

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsSupervisorOrAbove()]
        if self.action in {"checkin", "list", "retrieve"}:
            return [IsCajeroOrAbove()]
        return super().get_permissions()

    @action(methods=["post"], detail=False)
    def checkin(self, request):
        serializer = GuestCheckinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        guest = GuestEntry.objects.filter(qr_code=data["qr_code"]).first()
        if not guest:
            return Response({"detail": "Invitado no encontrado"}, status=status.HTTP_404_NOT_FOUND)
        if guest.status == GuestEntry.Status.ENTERED:
            return Response({"detail": "Este invitado ya ingreso"}, status=status.HTTP_400_BAD_REQUEST)

        companions_used = data["companions_used"]
        if companions_used > guest.companions_allowed:
            return Response({"detail": "Excede acompanantes permitidos"}, status=status.HTTP_400_BAD_REQUEST)

        guest.status = GuestEntry.Status.ENTERED
        guest.companions_used = companions_used
        guest.checked_in_at = timezone.now()
        guest.checked_in_by = request.user
        guest.save(update_fields=["status", "companions_used", "checked_in_at", "checked_in_by", "updated_at"])

        return Response(self.get_serializer(guest).data)
