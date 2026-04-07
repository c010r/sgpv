from django.contrib import admin

from settings_app.models import Bar, BarSession, SystemConfiguration

admin.site.register(SystemConfiguration)
admin.site.register(Bar)
admin.site.register(BarSession)
