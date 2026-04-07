from celery import shared_task
from django.db.models import Sum

from sales.models import Sale


@shared_task
def summarize_sales_total():
    total = Sale.objects.filter(status=Sale.Status.COMPLETED).aggregate(total=Sum("total"))["total"]
    return str(total or 0)
