"""
URL configuration for tender_project project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from tenders.views import UploadPageView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', UploadPageView.as_view(), name='home'),
    path('api/', include('tenders.urls')),
]

# Serve uploaded media files (PDFs) both in development and production
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

