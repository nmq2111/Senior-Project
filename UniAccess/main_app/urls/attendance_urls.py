from django.urls import path
from main_app import views

urlpatterns = [
    path("api/rfid/scan/", views.rfid_scan, name="rfid_scan"),
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("attendance/unassigned/", views.unassigned_list, name="unassigned_list"),
    path("attendance/assign/<int:record_id>/", views.assign_uid_to_user, name="assign_uid_to_user"),
]
