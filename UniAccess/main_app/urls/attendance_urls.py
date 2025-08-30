from django.urls import path
from main_app import views

urlpatterns = [
    path('staff/signup-assign/', views.admin_signup_assign_rfid, name='admin_signup_assign_rfid'),
    path('api/rfid/ingest/', views.ingest_scan, name='rfid_ingest'),
    path('api/rfid/recent-unassigned/', views.recent_unassigned_scans_api, name='recent_unassigned_scans_api'),

]
