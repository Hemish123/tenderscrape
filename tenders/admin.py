# tenders/admin.py
"""
Enhanced Django admin configuration for Tender and TenderDocument models.
Provides filtering, search, and formatted display for tender management.
"""

from django.contrib import admin
from .models import Tender, TenderDocument


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = (
        'tender_id', 'short_title', 'department', 'category',
        'location', 'source', 'closing_date', 'created_at',
    )
    list_filter = ('source', 'category', 'location', 'closing_date')
    search_fields = ('title', 'department', 'tender_id', 'location')
    list_per_page = 25
    ordering = ('-closing_date',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'closing_date'

    fieldsets = (
        ('Tender Details', {
            'fields': ('tender_id', 'title', 'department', 'category')
        }),
        ('Location & Source', {
            'fields': ('location', 'source', 'link')
        }),
        ('Dates', {
            'fields': ('closing_date', 'created_at')
        }),
    )

    def short_title(self, obj):
        """Display truncated title for readability."""
        return obj.title[:80] + '...' if len(obj.title) > 80 else obj.title
    short_title.short_description = 'Title'


@admin.register(TenderDocument)
class TenderDocumentAdmin(admin.ModelAdmin):
    list_display = ('tender', 'has_summary', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('tender__title', 'tender__tender_id')
    list_per_page = 25
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'raw_text', 'summary_json')

    fieldsets = (
        ('Linked Tender', {
            'fields': ('tender',)
        }),
        ('Extracted Data', {
            'fields': ('raw_text', 'summary_json', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def has_summary(self, obj):
        """Show whether a summary has been generated."""
        return bool(obj.summary_json)
    has_summary.boolean = True
    has_summary.short_description = 'Summary Generated'