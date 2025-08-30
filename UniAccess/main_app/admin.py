from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, Course, CourseInfo, Enrollment, Attendance, RFIDTag, RfidScan, Profile


admin.site.register([Course, CourseInfo, Enrollment, Attendance, RFIDTag, RfidScan, Profile])