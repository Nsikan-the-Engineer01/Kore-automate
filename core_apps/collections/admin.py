from django.contrib import admin
from .models import Collection


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('request_ref', 'user', 'goal', 'amount_total', 'currency', 'status', 'provider', 'created_at')
    list_filter = ('status', 'provider', 'currency', 'created_at')
    search_fields = ('request_ref', 'provider_ref', 'user__email', 'goal__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'goal')
        }),
        ('Amount Details', {
            'fields': ('amount_allocation', 'kore_fee', 'amount_total', 'currency')
        }),
        ('Provider Information', {
            'fields': ('provider', 'request_ref', 'provider_ref')
        }),
        ('Status & Narrative', {
            'fields': ('status', 'narrative')
        }),
        ('Request/Response Data', {
            'fields': ('raw_request', 'raw_response'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
