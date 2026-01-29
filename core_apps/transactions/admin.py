from django.contrib import admin
from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'amount', 'currency', 'status', 'occurred_at', 'request_ref', 'provider_ref')
    list_filter = ('type', 'status', 'currency', 'occurred_at')
    search_fields = ('request_ref', 'provider_ref', 'user__email')
    readonly_fields = ('id', 'user', 'goal', 'collection', 'type', 'amount', 'currency', 'request_ref', 'provider_ref', 'occurred_at', 'metadata', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Transaction Information', {
            'fields': ('id', 'request_ref', 'provider_ref')
        }),
        ('Related Objects', {
            'fields': ('user', 'goal', 'collection')
        }),
        ('Amount Details', {
            'fields': ('type', 'amount', 'currency')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timing', {
            'fields': ('occurred_at', 'created_at', 'updated_at')
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Disable manual creation via admin - should be created by business logic."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deletion - append-only ledger."""
        return False
