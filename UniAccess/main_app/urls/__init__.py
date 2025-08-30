from django.urls import path, include
from main_app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('main_app.urls.pages_url')),
    path('', include('main_app.urls.courses_urls')),
    # path('', include('main_app.urls.attendance_urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)