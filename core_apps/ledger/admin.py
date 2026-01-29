from django.contrib import admin
from .models import LedgerAccount, JournalEntry, LedgerLine


@admin.register(LedgerAccount)
class LedgerAccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'type')
    list_filter = ('type',)
    search_fields = ('code', 'name')
    readonly_fields = ('code',)
    
    fieldsets = (
        ('Account Information', {
            'fields': ('code', 'name', 'type')
        }),
    )


class LedgerLineInline(admin.TabularInline):
    model = LedgerLine
    extra = 1
    fields = ('account', 'debit', 'credit')
    raw_id_fields = ('account',)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'created_at', 'line_count')
    list_filter = ('created_at',)
    search_fields = ('reference', 'memo')
    readonly_fields = ('id', 'created_at')
    inlines = [LedgerLineInline]
    
    fieldsets = (
        ('Entry Information', {
            'fields': ('id', 'reference')
        }),
        ('Details', {
            'fields': ('memo', 'created_at')
        }),
    )
    
    def line_count(self, obj):
        return obj.lines.count()
    line_count.short_description = 'Lines'


@admin.register(LedgerLine)
class LedgerLineAdmin(admin.ModelAdmin):
    list_display = ('journal_entry', 'account', 'debit', 'credit', 'line_type')
    list_filter = ('journal_entry__created_at', 'account__type')
    search_fields = ('journal_entry__reference', 'account__code', 'account__name')
    readonly_fields = ('journal_entry',)
    raw_id_fields = ('account',)
    
    fieldsets = (
        ('Entry & Account', {
            'fields': ('journal_entry', 'account')
        }),
        ('Amounts', {
            'fields': ('debit', 'credit')
        }),
    )
    
    def line_type(self, obj):
        if obj.debit > 0:
            return 'Debit'
        else:
            return 'Credit'
    line_type.short_description = 'Type'
