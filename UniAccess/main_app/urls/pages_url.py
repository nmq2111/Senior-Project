from django.urls import path , include
from main_app import views


urlpatterns = [
        path('', views.home, name='home'),
        path('accounts/signup/', views.signup_view , name='signup'), 
       
]

