from django.contrib import admin

from sales.models import CashRegister, CashSession, Sale, SaleItem, SalePayment

admin.site.register(CashRegister)
admin.site.register(CashSession)
admin.site.register(Sale)
admin.site.register(SaleItem)
admin.site.register(SalePayment)
