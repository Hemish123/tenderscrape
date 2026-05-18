# tenders/views.py
"""
API views for the Tender Document Analysis System.

Uses async background processing to avoid Azure's 230-second gateway timeout.
Upload returns immediately, processing runs in a background thread,
and the frontend polls a status endpoint for results.
"""

import logging
import threading

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


def _process_document(doc_id: int):
    """
    Background task: extract text from PDF and generate AI summary.
    Updates the TenderDocument status as it progresses.
    Runs in a separate thread to avoid HTTP timeout.
    """
    import django
    django.setup()

    try:
        doc = TenderDocument.objects.get(pk=doc_id)
    except TenderDocument.DoesNotExist:
        logger.error("Document %d not found for processing", doc_id)
        return

    # --- Step 1: Extract text ---
    doc.status = TenderDocument.Status.EXTRACTING
    doc.save(update_fields=['status'])

    try:
        from .services.pdf_processor import extract_text_from_file
        try:
            file_source = doc.file.path
        except NotImplementedError:
            # Cloud storage backends (Azure, S3) don't support .path
            file_source = doc.file
        extracted_text = extract_text_from_file(file_source)
    except (ValueError, RuntimeError) as e:
        logger.error("PDF extraction failed for document %d: %s", doc_id, e)
        doc.status = TenderDocument.Status.FAILED
        doc.error_message = f'PDF processing failed: {str(e)}'
        doc.save(update_fields=['status', 'error_message'])
        return

    doc.extracted_text = extracted_text
    doc.save(update_fields=['extracted_text'])

    # --- Step 2: AI Summarization ---
    doc.status = TenderDocument.Status.ANALYZING
    doc.save(update_fields=['status'])

    try:
        from .services.ai_summarizer import generate_summary
        summary = generate_summary(extracted_text)
    except Exception as e:
        logger.error("AI summarization failed for document %d: %s", doc_id, e)
        doc.status = TenderDocument.Status.FAILED
        doc.error_message = f'AI summarization failed: {str(e)}'
        doc.save(update_fields=['status', 'error_message'])
        return

    # --- Step 3: Done ---
    doc.summary_json = summary
    doc.status = TenderDocument.Status.COMPLETED
    doc.error_message = ''
    doc.save(update_fields=['summary_json', 'status', 'error_message'])
    logger.info("Document %d processed successfully", doc_id)


class UploadTenderView(APIView):
    """
    POST /api/upload-tender/

    Upload a tender PDF and start async background processing.
    Returns immediately with the document ID so the frontend can poll.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            return self._handle_upload(request)
        except Exception as e:
            logger.exception("Unhandled error in UploadTenderView: %s", e)
            return Response(
                {'error': f'Internal server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _handle_upload(self, request):
        # 1. Validate uploaded file
        serializer = TenderUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        uploaded_file = serializer.validated_data['file']

        # 2. Save the document record
        doc = TenderDocument.objects.create(
            file=uploaded_file,
            status=TenderDocument.Status.PENDING,
        )

        # 3. Start background processing (avoids Azure gateway timeout)
        thread = threading.Thread(
            target=_process_document,
            args=(doc.pk,),
            daemon=True,
        )
        thread.start()

        # 4. Return immediately with the document ID
        return Response(
            {
                'status': 'accepted',
                'message': 'Document uploaded. Processing has started.',
                'data': {
                    'id': doc.pk,
                    'status': doc.status,
                },
            },
            status=status.HTTP_202_ACCEPTED,
        )


class TenderStatusView(APIView):
    """
    GET /api/tender/<id>/status/

    Poll this endpoint to check processing status.
    Returns the current status and, when complete, the full summary data.
    """
    def get(self, request, pk):
        try:
            doc = TenderDocument.objects.get(pk=pk)
        except TenderDocument.DoesNotExist:
            return Response(
                {'error': 'Tender document not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        response_data = {
            'id': doc.pk,
            'status': doc.status,
        }

        if doc.status == TenderDocument.Status.COMPLETED:
            serializer = TenderDocumentSerializer(
                doc, context={'request': request}
            )
            response_data['data'] = serializer.data

        elif doc.status == TenderDocument.Status.FAILED:
            response_data['error'] = doc.error_message or 'Processing failed.'

        return Response(response_data)


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