# tenders/urls.py
"""
URL configuration for the tenders API.
"""

from django.urls import path
from .views import TenderListView, FilterOptionsView, StatsView, TenderSummaryView

urlpatterns = [
    path('tenders/', TenderListView.as_view(), name='tender-list'),
    path('tenders/filters/', FilterOptionsView.as_view(), name='tender-filters'),
    path('tenders/stats/', StatsView.as_view(), name='tender-stats'),
    path('tender/<int:pk>/summary/', TenderSummaryView.as_view(), name='tender-summary'),
]