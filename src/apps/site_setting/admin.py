from django.contrib import admin

from .models import SiteSetting



@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):

    list_display = ('site_name', 'shamsi_modified_at')

    def has_add_permission(self, request):
        if SiteSetting.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False
    