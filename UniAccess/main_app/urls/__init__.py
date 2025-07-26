from django.urls import path, include
from main_app import views

urlpatterns = [
    path('', include('main_app.urls.pages_url')),
]

