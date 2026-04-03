# tenders/views.py
"""
API views for the tender management application.
Provides filtered, paginated, searchable tender listing and dynamic filter options.
"""

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q
from django.views.generic import TemplateView
from django.utils import timezone

from .models import Tender, TenderDocument
from .serializers import TenderSerializer, TenderDocumentSerializer


class HomeView(TemplateView):
    """Serve the main dashboard template."""
    template_name = 'index.html'


class TenderListView(generics.ListAPIView):
    """
    GET /api/tenders/
    
    Returns paginated list of tenders with support for:
    - category: Filter by category (case-insensitive contains)
    - location: Filter by location (case-insensitive contains)
    - source: Filter by source state (case-insensitive contains)
    - search: Search in title + department (case-insensitive)
    
    Results are sorted by closing_date descending (most recent first).
    """
    serializer_class = TenderSerializer

    def get_queryset(self):
        queryset = Tender.objects.all().order_by('-closing_date')

        # Category filter
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__icontains=category)

        # Location filter
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        # Source filter
        source = self.request.query_params.get('source')
        if source:
            queryset = queryset.filter(source__icontains=source)

        # Search filter (searches title + department)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(department__icontains=search)
            )

        return queryset


class FilterOptionsView(APIView):
    """
    GET /api/tenders/filters/
    
    Returns distinct values for category, location, and source fields.
    Used to dynamically populate filter dropdowns on the frontend.
    """
    def get(self, request):
        categories = (
            Tender.objects.exclude(category__isnull=True)
            .exclude(category='')
            .values_list('category', flat=True)
            .distinct()
            .order_by('category')
        )

        locations = (
            Tender.objects.exclude(location__isnull=True)
            .exclude(location='')
            .values_list('location', flat=True)
            .distinct()
            .order_by('location')
        )

        sources = (
            Tender.objects.exclude(source__isnull=True)
            .exclude(source='')
            .values_list('source', flat=True)
            .distinct()
            .order_by('source')
        )

        return Response({
            'categories': list(categories),
            'locations': list(locations),
            'sources': list(sources),
        })


class StatsView(APIView):
    """
    GET /api/tenders/stats/
    
    Returns aggregate statistics from the database:
    - total: Total number of tenders
    - active: Tenders with closing_date >= today (or null closing_date)
    - states: Number of distinct source states
    - categories: Number of distinct categories
    """
    def get(self, request):
        today = timezone.now().date()
        total = Tender.objects.count()
        active = Tender.objects.filter(
            Q(closing_date__gte=today) | Q(closing_date__isnull=True)
        ).count()
        states = (
            Tender.objects.exclude(source='')
            .values_list('source', flat=True)
            .distinct()
            .count()
        )
        categories = (
            Tender.objects.exclude(category__isnull=True)
            .exclude(category='')
            .values_list('category', flat=True)
            .distinct()
            .count()
        )

        return Response({
            'total': total,
            'active': active,
            'states': states,
            'categories': categories,
        })


class TenderSummaryView(APIView):
    """
    GET /api/tender/<id>/summary/

    Returns the AI-generated structured summary for a tender.
    - If a TenderDocument with summary already exists → return cached result.
    - Otherwise → download PDF → extract text → call Azure OpenAI → store → return.
    - If PDF is unavailable (e.g. eProcure tenders) → use tender metadata for summarization.
    """
    def get(self, request, pk):
        import logging
        logger = logging.getLogger('scrapers')

        # 1. Fetch the tender
        try:
            tender = Tender.objects.get(pk=pk)
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 2. Check for existing summary
        try:
            doc = TenderDocument.objects.get(tender=tender)
            if doc.summary_json:
                serializer = TenderDocumentSerializer(doc)
                return Response({
                    'status': 'cached',
                    'data': serializer.data,
                })
        except TenderDocument.DoesNotExist:
            doc = None

        # 3. Try to download and extract PDF text
        raw_text = None
        pdf_error = None
        try:
            from .services.pdf_processor import process_tender_pdf
            raw_text = process_tender_pdf(tender.link)
        except Exception as e:
            pdf_error = str(e)
            logger.warning(
                "PDF processing failed for tender %s: %s — falling back to metadata",
                pk, e
            )

        # 4. If PDF failed, build text from tender metadata
        if not raw_text:
            raw_text = self._build_metadata_text(tender)
            logger.info(
                "Using metadata text for tender %s (%d chars)", pk, len(raw_text)
            )

        # 5. Generate AI summary
        try:
            from .services.ai_summarizer import generate_summary
            summary = generate_summary(raw_text, tender.category or 'Other')
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error("AI summarization failed for tender %s: %s", pk, e)
            return Response(
                {'error': 'AI summarization failed: %s' % str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 6. Store the result
        if doc:
            doc.raw_text = raw_text
            doc.summary_json = summary
            doc.save()
        else:
            doc = TenderDocument.objects.create(
                tender=tender,
                raw_text=raw_text,
                summary_json=summary,
            )

        serializer = TenderDocumentSerializer(doc)
        resp_status = 'generated'
        if pdf_error:
            resp_status = 'generated_from_metadata'
        return Response({
            'status': resp_status,
            'data': serializer.data,
        })

    def _build_metadata_text(self, tender):
        """
        Build a text representation from tender metadata fields.
        Used when the PDF document is not available.
        """
        parts = []
        parts.append("Tender Title: %s" % (tender.title or 'N/A'))
        parts.append("Department: %s" % (tender.department or 'N/A'))
        parts.append("Category: %s" % (tender.category or 'N/A'))
        parts.append("Location: %s" % (tender.location or 'N/A'))
        parts.append("Source State: %s" % (tender.source or 'N/A'))
        if tender.closing_date:
            parts.append("Closing Date: %s" % tender.closing_date.strftime('%Y-%m-%d'))
        parts.append("Tender ID: %s" % (tender.tender_id or 'N/A'))
        parts.append("Link: %s" % (tender.link or 'N/A'))
        return '\n'.join(parts)