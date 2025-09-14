import json
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect , get_object_or_404
from ..forms import ProfileForm
from ..models import Profile , Enrollment, Attendance, RfidScan, CourseInfo, Course, RFIDTag
from datetime import timedelta, datetime as _dt, time as _time
from collections import defaultdict
from django.contrib import messages
from django.db.models import  Q, Subquery, OuterRef, IntegerField, Value, Count
from django.utils import timezone
from django.contrib.auth import get_user_model
from .course_views import is_registration_open
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models.functions import ExtractHour
from django.db.models.functions import Coalesce
from django.conf import settings
from django.http import HttpResponseForbidden



User = get_user_model()

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



def _weekday_token(dt):
    # 0=Mon ... 6=Sun
    idx = dt.weekday()
    # Matches the choices you used ('uth','mw','fs')
    return {
        0: "mw",   # Mon
        1: "uth",  # Tue
        2: "mw",   # Wed
        3: "uth",  # Thu
        4: "fs",   # Fri
        5: "fs",   # Sat
        6: "uth",  # Sun
    }[idx]

def _day_bucket_for_today(now=None):
    """
    Map weekday to your CourseInfo.days codes:
      - UTH: Sunday, Tuesday, Thursday
      - MW : Monday, Wednesday
      - FS : Friday, Saturday
    """
    now = now or timezone.localtime()
    wd = now.weekday()  # 0=Mon..6=Sun
    if wd in (1, 3, 6):   # Tue, Thu, Sun
        return "uth"
    if wd in (0, 2):      # Mon, Wed
        return "mw"
    return "fs"           # Fri, Sat


def student_dashboard(request):
    user = request.user
    if getattr(user, "role", None) != "student":
        messages.warning(request, "This page is for student accounts.")
        return redirect("home")

    # --- Pills ---
    reg_open = getattr(settings, "REGISTRATION_OPEN", True)
    tag_uid = getattr(getattr(user, "rfid_tag", None), "tag_uid", None)

    # --- Enrollments ---
    enrollments = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course_info", "course_info__course", "course_info__teacher")
        .order_by("course_info__course__code", "course_info__section")
    )

    # Warning distribution (levels 0..3)
    warn_counts = [0, 0, 0, 0]
    for e in enrollments:
        lvl = int(e.attendance_warning_level or 0)
        if   lvl <= 0: warn_counts[0] += 1
        elif lvl == 1: warn_counts[1] += 1
        elif lvl == 2: warn_counts[2] += 1
        else:          warn_counts[3] += 1

    # --- Attendance last 30 days ---
    today = timezone.localdate()
    since = today - timedelta(days=30)
    last30 = (
        Attendance.objects
        .filter(student=user, session_date__gte=since)
        .values("status")
        .annotate(c=Count("id"))
    )
    c_map = {r["status"]: r["c"] for r in last30}
    present = c_map.get("PRESENT", 0)
    late    = c_map.get("LATE", 0)
    absent  = c_map.get("ABSENT", 0)

    # --- Today’s classes (by bucket) ---
    bucket = _day_bucket_for_today()
    todays_classes = [e.course_info for e in enrollments if (e.course_info.days or "").lower() == bucket]
    todays_classes.sort(key=lambda ci: (ci.start_time, ci.course.code))

    # Next class today (based on local time)
    now = timezone.localtime()
    next_class = None
    for ci in todays_classes:
        if ci.start_time >= now.time():
            next_class = ci
            break

    # --- Recent attendance/scans ---
    recent_attendance = (
        Attendance.objects
        .filter(student=user)
        .select_related("course_info", "course_info__course")
        .order_by("-session_date", "-first_seen")[:10]
    )
    recent_scans = (
        RfidScan.objects
        .filter(user=user)
        .order_by("-created_at")[:10]
    )

    # --- Charts data ---
    att_pie = {
        "labels": ["Present", "Late", "Absent"],
        "data": [present, late, absent],
    }
    warn_bars = {
        "labels": ["Level 0", "Level 1", "Level 2", "Level 3"],
        "data": warn_counts,
    }

    # ---------------------------------------------------------
    # Full-week timetable (real day titles + time slots)
    # ---------------------------------------------------------
    DAY_ORDER_FULL = [
        ("sun", "Sunday"),
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
    ]
    BUCKET_TO_DAYS = {"uth": ["sun", "tue", "thu"], "mw": ["mon", "wed"], "fs": ["fri", "sat"]}

    # Collect sections per real day; detect min/max times
    week_grid = {k: [] for k, _ in DAY_ORDER_FULL}
    min_t, max_t = None, None

    for e in enrollments:
        ci = e.course_info
        days_key = (ci.days or "").lower()  # 'uth' / 'mw' / 'fs'
        for dk in BUCKET_TO_DAYS.get(days_key, []):
            week_grid[dk].append(ci)
        # track global time range for grid
        if min_t is None or ci.start_time < min_t:
            min_t = ci.start_time
        if max_t is None or ci.end_time > max_t:
            max_t = ci.end_time

    # Sort each day by start time
    for k in week_grid:
        week_grid[k].sort(key=lambda c: (c.start_time, c.course.code))

    # Round time range to hours; fallback 08:00–18:00 if empty
    def _round_down_hour(t: _time) -> _time:
        return _time(t.hour, 0)

    def _round_up_hour(t: _time) -> _time:
        if t.minute == 0 and t.second == 0:
            return _time(t.hour, 0)
        base = _dt.combine(today, t) + timedelta(hours=1)
        return _time(base.hour, 0)

    start_slot = _round_down_hour(min_t) if min_t else _time(8, 0)
    end_slot   = _round_up_hour(max_t) if max_t else _time(18, 0)

    # Build hourly slots (change to minutes=30 for half-hours if you like)
    week_slots = []
    cur = _dt.combine(today, start_slot)
    end_dt = _dt.combine(today, end_slot)
    while cur <= end_dt:
        week_slots.append(cur.time())
        cur += timedelta(hours=1)

    # Make template-friendly rows: each row has slot + a list of "cells"
    # cells[i] corresponds to DAY_ORDER_FULL[i]
    day_keys = [k for k, _ in DAY_ORDER_FULL]
    week_table_rows = []
    for slot in week_slots:
        cells = []
        for dk in day_keys:
            cell_items = [ci for ci in week_grid[dk] if ci.start_time <= slot < ci.end_time]
            cells.append(cell_items)
        week_table_rows.append({"slot": slot, "cells": cells})

    context = {
        "reg_open": reg_open,
        "tag_uid": tag_uid,

        "enrollments": enrollments,

        "present": present,
        "late": late,
        "absent": absent,

        "today": today,
        "todays_classes": todays_classes,
        "next_class": next_class,

        "recent_attendance": recent_attendance,
        "recent_scans": recent_scans,

        # charts
        "att_pie": att_pie,
        "warn_bars": warn_bars,

        # full-day timetable
        "day_order_full": DAY_ORDER_FULL,  # for headers
        "week_table_rows": week_table_rows,  # [{slot, cells:[ [ci...], ... ]}]
    }
    return render(request, "dashboard/student_dashboard.html", context)



@login_required
def student_attendance(request):
    user = request.user
    if getattr(user, "role", None) != "student":
        messages.warning(request, "This page is for student accounts.")
        return redirect("home")

    # ---------- Filters ----------
    q          = (request.GET.get("q") or "").strip()
    status     = (request.GET.get("status") or "").strip()
    section_id = (request.GET.get("course_info") or "").strip()
    start      = (request.GET.get("start") or "").strip()  # YYYY-MM-DD
    end        = (request.GET.get("end") or "").strip()    # YYYY-MM-DD
    order      = (request.GET.get("order") or "-session_date").strip()

    # Base queryset: ONLY this student's records
    qs = Attendance.objects.select_related(
        "course_info",
        "course_info__course",
        "course_info__teacher",
    ).filter(student=user)

    # Search (code/name/class/teacher)
    if q:
        qs = qs.filter(
            Q(course_info__course__code__icontains=q) |
            Q(course_info__course__name__icontains=q) |
            Q(course_info__class_name__icontains=q) |
            Q(course_info__teacher__username__icontains=q) |
            Q(course_info__teacher__first_name__icontains=q) |
            Q(course_info__teacher__last_name__icontains=q)
        )

    # Status filter
    if status:
        qs = qs.filter(status=status)

    # Section filter
    if section_id:
        try:
            qs = qs.filter(course_info_id=int(section_id))
        except ValueError:
            pass

    # Date range
    def _parse_date(s):
        try:
            return _time.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    start_d = _parse_date(start)
    end_d   = _parse_date(end)
    if start_d:
        qs = qs.filter(session_date__gte=start_d)
    if end_d:
        qs = qs.filter(session_date__lte=end_d)

    # Annotate warning level from Enrollment (student, course_info)
    subq = Enrollment.objects.filter(
        student_id=user.id,
        course_info_id=OuterRef("course_info_id"),
    ).values("attendance_warning_level")[:1]

    qs = qs.annotate(
        warn_level=Coalesce(Subquery(subq, output_field=IntegerField()), Value(0))
    )

    # Sorting (whitelist)
    allowed_order = {
        "session_date", "-session_date",
        "first_seen", "-first_seen",
        "status", "-status",
        "course_info__course__code", "-course_info__course__code",
        "course_info__class_name", "-course_info__class_name",
    }
    if order not in allowed_order:
        order = "-session_date"

    records = qs.order_by(order)[:1000]  # soft cap

    status_counts = (
        Attendance.objects
        .filter(student=user)
        .values("status")
        .annotate(c=Count("id"))
    )
    counts_map = {r["status"]: r["c"] for r in status_counts}
    present = counts_map.get("PRESENT", 0)
    late    = counts_map.get("LATE", 0)
    absent  = counts_map.get("ABSENT", 0)

    my_sections = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course_info", "course_info__course", "course_info__teacher")
        .order_by("course_info__course__code", "course_info__section")
    )
    section_opts = [
        {
            "id": e.course_info.id,
            "label": f"{e.course_info.course.code} – {e.course_info.class_name} (Sec {getattr(e.course_info, 'section', '—')})",
            "teacher": (e.course_info.teacher.get_full_name() or e.course_info.teacher.username),
        }
        for e in my_sections
    ]

    context = {
        "records": records,

        "q": q,
        "status": status,
        "section_id": section_id,
        "start": start,
        "end": end,
        "order": order,

        "status_opts": Attendance.STATUS_CHOICES,
        "section_opts": section_opts,

        "present": present,
        "late": late,
        "absent": absent,
    }
    return render(request, "registration/student_attendance.html", context)




def _is_teacher(user):
    return getattr(user, "role", None) == "teacher" or user.is_staff or user.is_superuser


@login_required
def teacher_dashboard(request):
    user = request.user
    if not _is_teacher(user):
        return HttpResponseForbidden("Teachers only.")

    # --- Sections taught by this teacher ---
    sections = (
        CourseInfo.objects
        .filter(teacher=user)
        .select_related("course", "teacher")
        .annotate(enrolled_count=Count("enrollments", distinct=True))
        .order_by("course__code", "section", "class_name")
    )

    # Totals
    total_sections = sections.count()
    total_students = (
        Enrollment.objects
        .filter(course_info__teacher=user)
        .values("student_id").distinct().count()
    )

    # --- Today ---
    today = timezone.localdate()
    bucket = _day_bucket_for_today(today)
    todays_sections = [ci for ci in sections if (ci.days or "").lower() == bucket]
    todays_sections.sort(key=lambda ci: (ci.start_time, ci.course.code))

    # Compute "next class"
    now_local = timezone.localtime()
    next_class = None
    for ci in todays_sections:
        if ci.start_time >= now_local.time():
            next_class = ci
            break

    # Attendance today (across my sections)
    att_today_qs = Attendance.objects.filter(
        course_info__teacher=user,
        session_date=today,
    )
    today_present = att_today_qs.filter(status="PRESENT").count()
    today_late    = att_today_qs.filter(status="LATE").count()
    today_absent  = att_today_qs.filter(status="ABSENT").count()

    # --- Last 30 days attendance distribution ---
    since = today - timedelta(days=30)
    last30 = (
        Attendance.objects
        .filter(course_info__teacher=user, session_date__gte=since)
        .values("status").annotate(c=Count("id"))
    )
    c_map = {r["status"]: r["c"] for r in last30}
    present30 = c_map.get("PRESENT", 0)
    late30    = c_map.get("LATE", 0)
    absent30  = c_map.get("ABSENT", 0)

    # --- Warning levels across my sections (if you store them on Enrollment) ---
    warn_counts = [0, 0, 0, 0]  # 0..3
    for lvl, count in (
        Enrollment.objects
        .filter(course_info__teacher=user)
        .values_list("attendance_warning_level")
        .annotate(c=Count("id"))
    ):
        lvl = int(lvl or 0)
        if   lvl <= 0: warn_counts[0] += count
        elif lvl == 1: warn_counts[1] += count
        elif lvl == 2: warn_counts[2] += count
        else:          warn_counts[3] += count

    # --- Recent attendance & scans (for my sections) ---
    recent_attendance = (
        Attendance.objects
        .filter(course_info__teacher=user)
        .select_related("course_info", "course_info__course", "student")
        .order_by("-session_date", "-first_seen")[:12]
    )
    recent_scans = (
        RfidScan.objects
        .filter(user__enrollments__course_info__teacher=user)
        .order_by("-created_at")
        .distinct()[:12]
    )

    # --- Week groups (UTH/MW/FS) ---
    week_groups = {"uth": [], "mw": [], "fs": []}
    for ci in sections:
        key = (ci.days or "").lower()
        if key in week_groups:
            week_groups[key].append(ci)
    for k in week_groups:
        week_groups[k].sort(key=lambda ci: ci.start_time)

    # Chart payloads
    att_pie = {"labels": ["Present", "Late", "Absent"], "data": [present30, late30, absent30]}
    warn_bars = {"labels": ["Level 0", "Level 1", "Level 2", "Level 3"], "data": warn_counts}

    context = {
        "today": today,
        "sections": sections,
        "total_sections": total_sections,
        "total_students": total_students,

        "todays_sections": todays_sections,
        "next_class": next_class,

        "today_present": today_present,
        "today_late": today_late,
        "today_absent": today_absent,

        "recent_attendance": recent_attendance,
        "recent_scans": recent_scans,

        "week_groups": week_groups,

        # charts
        "att_pie": att_pie,
        "warn_bars": warn_bars,
    }
    return render(request, "dashboard/teacher_dashboard.html", context)