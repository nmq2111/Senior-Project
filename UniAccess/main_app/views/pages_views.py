from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from ..forms import ProfileForm
from ..models import Profile


def home(request):
    return render(request, 'home.html')



@login_required
def view_Profile(request):
    return render(request, 'Profile.html')


@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('Profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile_edit.html', {'form': form})


# main_app/views/admin_views.py
import json
from datetime import datetime, timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, F
from django.db.models.functions import ExtractHour
from django.shortcuts import render
from django.utils import timezone

from ..models import Course, CourseInfo, Enrollment, RFIDTag, RfidScan, Attendance

User = get_user_model()

def _today_range():
    now = timezone.localtime()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start, end




@staff_member_required
def admin_dashboard(request):
    now = timezone.localtime()
    start_today, end_today = _today_range()

    # ---- Top counters
    counts = {
        "students": User.objects.filter(role="student").count(),
        "teachers": User.objects.filter(role="teacher").count(),
        "admins":   User.objects.filter(role="admin").count(),
        "courses":  Course.objects.count(),
        "sections": CourseInfo.objects.count(),
        "enrollments": Enrollment.objects.count(),
        "tags_total": RFIDTag.objects.count(),
        "tags_assigned": RFIDTag.objects.filter(assigned_to__isnull=False).count(),
        "tags_unassigned": RFIDTag.objects.filter(assigned_to__isnull=True).count(),
        "scans_today": RfidScan.objects.filter(created_at__gte=start_today, created_at__lt=end_today).count(),
        "unknown_scans_today": RfidScan.objects.filter(
            created_at__gte=start_today, created_at__lt=end_today, user__isnull=True
        ).count(),
    }

    # ---- Attendance today + breakdown
    att_today = Attendance.objects.filter(first_seen__gte=start_today, first_seen__lt=end_today)
    by_status = dict(att_today.values_list("status").annotate(c=Count("id")))
    att_present = by_status.get("PRESENT", 0)
    att_late = by_status.get("LATE", 0)
    att_absent = by_status.get("ABSENT", 0)

    att_pie = {
        "labels": ["Present", "Late", "Absent"],
        "data": [att_present, att_late, att_absent],
    }

    # ---- Active sections right now
    t = now.time()
    active_sections = (
        CourseInfo.objects
        .select_related("course", "teacher")
        .filter(status__in=["Yes", "Available"], start_time__lte=t, end_time__gte=t)
        .order_by("course__code", "class_name")[:8]
    )

    # ---- Scans by hour (today)
    scans_by_hour_qs = (
        RfidScan.objects
        .filter(created_at__gte=start_today, created_at__lt=end_today)
        .annotate(h=ExtractHour("created_at"))
        .values("h").annotate(c=Count("id")).order_by("h")
    )
    scans_map = {row["h"]: row["c"] for row in scans_by_hour_qs}
    scans_hour_labels = list(range(24))
    scans_hour_counts = [scans_map.get(h, 0) for h in scans_hour_labels]

    # ---- Recent unknown scans
    recent_unknown_scans = (
        RfidScan.objects.filter(created_at__gte=start_today, created_at__lt=end_today, user__isnull=True)
        .order_by("-created_at")
        .values("uid", "device_id", "created_at")[:10]
    )

    # ---- Students without tags (top 10 newest)
    tagless_students = (
        User.objects.filter(role="student", rfid_tag__isnull=True)
        .order_by("-date_joined")
        .values("id", "username", "first_name", "last_name", "custom_id")[:10]
    )

    context = {
        "now": now,
        "counts": counts,
        "active_sections": active_sections,
        "recent_unknown_scans": recent_unknown_scans,
        "tagless_students": tagless_students,
        "att_pie_json": json.dumps(att_pie),
        "scans_hour_labels_json": json.dumps(scans_hour_labels),
        "scans_hour_counts_json": json.dumps(scans_hour_counts),
    }
    return render(request, "dashboard/admin_dashboard.html", context)

