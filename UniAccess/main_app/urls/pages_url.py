from django.urls import path , include
from main_app import views


urlpatterns = [
        path('', views.home, name='home'),
        path('accounts/Profile/', views.view_Profile , name='Profile'),
        path('accounts/profile/edit/', views.edit_profile, name='edit_profile'), 
]

