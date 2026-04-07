import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from guests.models import GuestImportJob, GuestList


@pytest.mark.django_db
def test_guest_import_creates_job_with_errors(supervisor):
    guest_list = GuestList.objects.create(name="Import Job List", event_date="2026-04-20", created_by=supervisor)
    csv_content = "full_name,qr_code,document_id\nJohn,QR-1,123\nBadLine,,456\n"
    upload = SimpleUploadedFile("guests.csv", csv_content.encode("utf-8"), content_type="text/csv")

    client = APIClient()
    client.force_authenticate(user=supervisor)

    response = client.post(f"/api/listas-invitados/{guest_list.id}/import_csv/", {"file": upload}, format="multipart")
    assert response.status_code == 200
    job_id = response.data["job_id"]

    job = GuestImportJob.objects.get(id=job_id)
    assert job.total_rows == 2
    assert job.created_rows == 1
    assert job.error_rows == 1
    assert job.errors.count() == 1
