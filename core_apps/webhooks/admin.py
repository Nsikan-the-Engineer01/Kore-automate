from django.contrib import admin
from .models import WebhookEvent


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'provider', 'request_ref', 'status', 'received_at', 'processed_at')
    list_filter = ('provider', 'status', 'received_at', 'processed_at')
    search_fields = ('event_id', 'request_ref', 'provider')
    readonly_fields = ('id', 'received_at', 'payload')
    
    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'provider', 'event_id', 'request_ref')
        }),
        ('Webhook Data', {
            'fields': ('payload', 'signature')
        }),
        ('Processing Status', {
            'fields': ('status', 'error')
        }),
        ('Timestamps', {
            'fields': ('received_at', 'processed_at')
        }),
    )
