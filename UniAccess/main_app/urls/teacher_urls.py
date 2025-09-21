from django.urls import path
from main_app import views

urlpatterns = [
    path("teacher/attendance/", views.teacher_attendance_list, name="teacher_attendance_list"),
    path("teacher/attendance/section/<int:course_info_id>/", views.teacher_take_attendance, name="teacher_take_attendance"),
    path("teacher/attendance/edit/<int:pk>/", views.TeacherAttendanceEdit.as_view(), name="teacher_attendance_edit"),
    path("teacher/attendance/take/course/", views.attendance_take_C, name="attendance_take_C"),
    path("teacher/users/", views.teacher_userbase, name="teacher_userbase"),
    path("teacher/sections/<int:course_info_id>/finish/", views.finish_lecture, name="finish_lecture"),

]

