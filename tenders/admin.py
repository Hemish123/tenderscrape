# tenders/admin.py
"""
Django admin configuration for TenderDocument model.
"""

from django.contrib import admin
from .models import TenderDocument


@admin.register(TenderDocument)
class TenderDocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'file', 'has_summary', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('file',)
    list_per_page = 25
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'extracted_text', 'summary_json')

    fieldsets = (
        ('Uploaded File', {
            'fields': ('file',)
        }),
        ('Extracted Data', {
            'fields': ('extracted_text', 'summary_json', 'created_at'),
            'classes': ('collapse',),
        }),
    )

    def has_summary(self, obj):
        """Show whether a summary has been generated."""
        return bool(obj.summary_json)
    has_summary.boolean = True
    has_summary.short_description = 'Summary Generated'