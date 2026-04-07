from django.contrib import admin

from guests.models import GuestEntry, GuestList

admin.site.register(GuestList)
admin.site.register(GuestEntry)
