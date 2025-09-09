from django.urls import path
from main_app import views

urlpatterns = [
    path("user/studentYear/", views._student_year_options, name="_student_year_options"),
    path("user/directory/", views.users_directory, name="users_directory"),
    path("accounts/staff/", views.create_staff , name='create_staff'), 
    path("accounts/student/", views.admin_create_student, name="admin_create_student"),
    path("attendance/student/", views.attendance_list, name="attendance_list"),
]
