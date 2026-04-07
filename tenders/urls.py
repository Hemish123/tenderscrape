# tenders/urls.py
"""
URL configuration for the tender document analysis API.
"""

from django.urls import path
from .views import UploadTenderView, TenderDetailView

urlpatterns = [
    path('upload-tender/', UploadTenderView.as_view(), name='upload-tender'),
    path('tender/<int:pk>/', TenderDetailView.as_view(), name='tender-detail'),
]