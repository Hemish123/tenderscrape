# tenders/models.py
"""
Data models for the Tender Document Analysis System.
"""

from django.db import models


class TenderDocument(models.Model):
    """
    Stores an uploaded tender PDF, its extracted text,
    and the AI-generated structured summary.
    """
    file = models.FileField(upload_to='tender_pdfs/')
    extracted_text = models.TextField(blank=True, default='')
    summary_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TenderDocument #{self.pk} — {self.file.name}"

    class Meta:
        ordering = ['-created_at']