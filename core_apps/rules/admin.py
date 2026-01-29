from django.contrib import admin
from .models import Rule


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    list_display = ('goal', 'user', 'frequency', 'amount', 'enabled', 'last_run_at', 'created_at')
    list_filter = ('frequency', 'enabled', 'created_at')
    search_fields = ('user__email', 'goal__name')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_run_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'goal')
        }),
        ('Rule Configuration', {
            'fields': ('frequency', 'amount', 'enabled')
        }),
        ('Execution', {
            'fields': ('last_run_at',)
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
