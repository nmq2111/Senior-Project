from django.urls import path
from main_app import views

urlpatterns = [
    # API endpoints
    path("api/rfid/scan/", views.rfid_scan, name="rfid_scan"),
    path("api/rfid/assign/", views.tag_to_student, name="tag_to_student"),

    # Staff UI
    path("staff/create-student/", views.admin_create_student, name="admin_create_student"),

    # Optional refresh endpoint for the dropdown
    path("api/rfid/latest-unassigned/", views.latest_unassigned_uids_api, name="latest_unassigned_uids"),
]
