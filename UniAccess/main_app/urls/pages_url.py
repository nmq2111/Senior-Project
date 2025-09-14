from django.urls import path , include
from main_app import views


urlpatterns = [
        path('', views.home, name='home'),
        path('accounts/Profile/', views.view_Profile , name='Profile'),
        path('accounts/profile/edit/', views.edit_profile, name='edit_profile'),
        path("dashboard/admin_dashboard/", views.admin_dashboard, name="admin_dashboard"),     
        path("dashboard/student_dashboard/", views.student_dashboard, name="student_dashboard"), 
        path("attendance/student_attendance/", views.student_attendance, name="student_attendance"),   
        path("dashboard/teacher/", views.teacher_dashboard, name="teacher_dashboard"),
]

