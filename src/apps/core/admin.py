from django.contrib import admin

from apps.core.models.idempotency import IdempotencyRecord


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    """
    Read-only on purpose.

    Editing one of these rows lets the same financial request be replayed for
    real, so the admin is a viewer. Resolving a stuck key means fixing the
    underlying operation, not clearing the row.
    """

    list_display = ['endpoint', 'key', 'user', 'status', 'reference', 'created_at']
    list_filter = ['endpoint', 'status']
    search_fields = ['key', 'reference', 'correlation_id']
    readonly_fields = [f.name for f in IdempotencyRecord._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
