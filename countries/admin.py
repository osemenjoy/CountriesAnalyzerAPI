from django.contrib import admin
from .models import Country, RefreshStatus

admin.site.register(Country)
admin.site.register(RefreshStatus)

# Register your models here.
