from django.urls import path
from main_app.views import pages_views as views


urlpatterns = [
        path('', views.home, name='home'),
]

