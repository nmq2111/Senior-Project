from django.urls import path, include
from . import views
from . import admin
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
  path('admin/', admin.site.urls),
  path('', include('main_app.urls')),

]  + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
