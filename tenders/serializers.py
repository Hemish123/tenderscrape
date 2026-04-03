# tenders/serializers.py
"""
DRF serializers for the Tender and TenderDocument models.
"""

from rest_framework import serializers
from .models import Tender, TenderDocument


class TenderSerializer(serializers.ModelSerializer):
    """Serializer for the Tender model — exposes all fields."""
    class Meta:
        model = Tender
        fields = '__all__'


class TenderDocumentSerializer(serializers.ModelSerializer):
    """Serializer for the TenderDocument model — exposes summary data."""
    tender_id = serializers.IntegerField(source='tender.id', read_only=True)
    tender_title = serializers.CharField(source='tender.title', read_only=True)
    category = serializers.CharField(source='tender.category', read_only=True)

    class Meta:
        model = TenderDocument
        fields = [
            'id', 'tender_id', 'tender_title', 'category',
            'summary_json', 'created_at',
        ]