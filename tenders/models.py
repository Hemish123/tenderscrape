# tenders/models.py

from django.db import models


class Tender(models.Model):
    """
    Represents a government tender scraped from state e-procurement portals.
    Each tender is uniquely identified by its tender_id to prevent duplicates.
    """
    tender_id = models.CharField(max_length=200, unique=True, db_index=True)
    title = models.TextField()
    department = models.CharField(max_length=500, null=True, blank=True)
    category = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    location = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    closing_date = models.DateField(null=True, blank=True, db_index=True)
    source = models.CharField(max_length=100, db_index=True)
    link = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.source}] {self.title[:80]}"

    class Meta:
        ordering = ['-closing_date']
        indexes = [
            models.Index(fields=['category', 'location']),
            models.Index(fields=['source', 'closing_date']),
        ]


class TenderDocument(models.Model):
    """
    Stores the extracted PDF text and AI-generated structured summary
    for a specific tender. Created on-demand when a user requests a summary.
    """
    tender = models.OneToOneField(
        Tender, on_delete=models.CASCADE, related_name='document'
    )
    raw_text = models.TextField(blank=True, default='')
    summary_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Document for {self.tender.tender_id}"

    class Meta:
        ordering = ['-created_at']