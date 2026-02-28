from django.contrib import admin
from .models import Activity, EmissionFactor

@admin.register(EmissionFactor)
class EmissionFactorAdmin(admin.ModelAdmin):
    # These names MUST match the fields in models.py exactly
    list_display = ('key', 'activity_type', 'co2e_per_unit', 'status', 'is_verified_factor')
    list_editable = ('status', 'is_verified_factor') # Quick edit from the list!
    list_filter = ('status', 'activity_type')

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'co2e', 'is_verified')