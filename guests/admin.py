from django.contrib import admin

from guests.models import GuestEntry, GuestImportJob, GuestImportJobError, GuestList

admin.site.register(GuestList)
admin.site.register(GuestEntry)
admin.site.register(GuestImportJob)
admin.site.register(GuestImportJobError)
