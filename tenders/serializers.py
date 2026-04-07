# tenders/serializers.py
"""
DRF serializers for the TenderDocument model.
Handles PDF upload validation and structured response output.
"""

from rest_framework import serializers
from .models import TenderDocument


class TenderUploadSerializer(serializers.Serializer):
    """Validates uploaded tender PDF file."""
    file = serializers.FileField()

    def validate_file(self, value):
        # Check file extension
        if not value.name.lower().endswith('.pdf'):
            raise serializers.ValidationError(
                "Only PDF files are accepted. Please upload a .pdf file."
            )

        # Check file size (max 20 MB)
        max_size = 20 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File too large. Maximum size is 20 MB, got {value.size / (1024*1024):.1f} MB."
            )

        # Check content type
        if hasattr(value, 'content_type') and value.content_type not in (
            'application/pdf', 'application/x-pdf',
        ):
            # Some browsers may send different content types, so just warn
            pass

        return value


class TenderDocumentSerializer(serializers.ModelSerializer):
    """Serializer for the TenderDocument model — returns summary data."""
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TenderDocument
        fields = ['id', 'file_url', 'summary_json', 'created_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None