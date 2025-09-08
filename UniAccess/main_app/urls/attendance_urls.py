from django.urls import path
from main_app import views

urlpatterns = [
    # API endpoints
    path("api/rfid/scan/", views.rfid_scan, name="rfid_scan"),
    path("api/rfid/assign/", views.tag_to_student, name="tag_to_student"),
    path("api/rfid/courseinfo/", views.find_current_courseinfo_for_student , name="find_current_courseinfo_for_student"),
    path("api/rfid/latest-unassigned/", views.latest_unassigned_uids_api, name="latest_unassigned_uids"),  
]
