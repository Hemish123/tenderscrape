"""
URL configuration for tender_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from tenders.views import UploadPageView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', UploadPageView.as_view(), name='home'),
    path('api/', include('tenders.urls')),
]

# Serve uploaded media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
