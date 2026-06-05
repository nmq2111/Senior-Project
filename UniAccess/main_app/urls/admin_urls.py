from django.urls import path
from main_app import views

urlpatterns = [
    path("user/studentYear/", views._student_year_options, name="_student_year_options"),
    path("user/directory/", views.users_directory, name="users_directory"),
    path("accounts/staff/", views.create_staff , name='create_staff'), 
    path("accounts/student/", views.admin_create_student, name="admin_create_student"),
    path("attendance/student/", views.attendance_list, name="attendance_list"),
    path("user/<int:user_id>/edit/",   views.admin_user_edit,  name="admin_user_edit"),
    path("user/<int:user_id>/delete/", views.admin_user_delete, name="admin_user_delete"),
]
