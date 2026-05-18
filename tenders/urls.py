# tenders/urls.py
"""
URL configuration for the tender document analysis API.
"""

from django.urls import path
from .views import UploadTenderView, TenderDetailView, TenderStatusView

urlpatterns = [
    path('upload-tender/', UploadTenderView.as_view(), name='upload-tender'),
    path('tender/<int:pk>/', TenderDetailView.as_view(), name='tender-detail'),
    path('tender/<int:pk>/status/', TenderStatusView.as_view(), name='tender-status'),
]