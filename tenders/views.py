# tenders/views.py
"""
API views for the Tender Document Analysis System.
Provides PDF upload, AI summarization, and retrieval endpoints.
"""

import logging

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from django.views.generic import TemplateView

from .models import TenderDocument
from .serializers import TenderUploadSerializer, TenderDocumentSerializer

logger = logging.getLogger(__name__)


class UploadPageView(TemplateView):
    """Serve the upload + result UI template."""
    template_name = 'upload.html'


class UploadTenderView(APIView):
    """
    POST /api/upload-tender/

    Upload a tender PDF, extract text, send to Azure OpenAI,
    and return the structured summary.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        # 1. Validate uploaded file
        serializer = TenderUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = serializer.validated_data['file']

        # 2. Save the document record with the uploaded file
        doc = TenderDocument.objects.create(file=uploaded_file)

        # 3. Extract text from the saved PDF
        try:
            from .services.pdf_processor import extract_text_from_file
            extracted_text = extract_text_from_file(doc.file.path)
        except (ValueError, RuntimeError) as e:
            logger.error("PDF extraction failed for document %d: %s", doc.pk, e)
            doc.delete()
            return Response(
                {'error': f'PDF processing failed: {str(e)}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # 4. Generate AI summary
        try:
            from .services.ai_summarizer import generate_summary
            summary = generate_summary(extracted_text)
        except ValueError as e:
            doc.delete()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("AI summarization failed for document %d: %s", doc.pk, e)
            # Still save the extracted text even if AI fails
            doc.extracted_text = extracted_text
            doc.save()
            return Response(
                {'error': f'AI summarization failed: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 5. Store results
        doc.extracted_text = extracted_text
        doc.summary_json = summary
        doc.save()

        # 6. Return response
        response_serializer = TenderDocumentSerializer(
            doc, context={'request': request}
        )
        return Response(
            {
                'status': 'success',
                'message': 'Tender document analyzed successfully.',
                'data': response_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class TenderDetailView(APIView):
    """
    GET /api/tender/<id>/

    Return the stored summary for a previously uploaded tender document.
    """
    def get(self, request, pk):
        try:
            doc = TenderDocument.objects.get(pk=pk)
        except TenderDocument.DoesNotExist:
            return Response(
                {'error': 'Tender document not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TenderDocumentSerializer(
            doc, context={'request': request}
        )
        return Response({
            'status': 'success',
            'data': serializer.data,
        })