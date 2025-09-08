from django.urls import path
from main_app import views

urlpatterns = [
    path("api/rfid/scan/", views.rfid_scan, name="rfid_scan"),
    path("api/rfid/assign/", views.tag_to_student, name="tag_to_student"),
    path("api/student/", views.is_student_enrolled , name="is_student_enrolled"),
]
