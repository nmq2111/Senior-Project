from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from ..models import Profile, Attendance, CourseInfo, Course, Enrollment
from django.shortcuts import render, redirect
from ..forms import CustomUserCreationForm, AdminCreateStudentForm
from django.urls import reverse
from datetime import datetime
from django.core.cache import cache
from .course_views import is_registration_open
from django.db.models import Q, Subquery, OuterRef, IntegerField, Value
from django.db.models.functions import Coalesce

User = get_user_model()

# === Helpers ===
def _student_year_options():
    years = (
        User.objects.filter(role="student")
        .dates("date_joined", "year", order="DESC")
    )
    return [d.year for d in years]

def _parse_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


# === Views ===
@staff_member_required
def users_directory(request):
    q = (request.GET.get("q") or "").strip()
    college = (request.GET.get("college") or "").strip()
    year = (request.GET.get("year") or "").strip()

    students = User.objects.filter(role="student").select_related("profile", "rfid_tag")

    if college:
        students = students.filter(college=college)

    if year:
        try:
            y = int(year)
            students = students.filter(date_joined__year=y)
        except ValueError:
            messages.warning(request, "Invalid year filter; ignored.")

    if q:
        students = students.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(custom_id__icontains=q) |
            Q(email__icontains=q)
        )

    students = students.order_by("-date_joined", "username")[:1000]
    staff = User.objects.filter(role__in=["teacher", "admin"]).order_by("role", "username")
    tags = (
        User.objects
        .filter(role="student")
        .select_related("tag_uid", "profile")
        .order_by("role", "username")
    )

    context = {
        "q": q,
        "college": college,
        "year": year,
        "college_opts": User.COLLEGE_CHOICES,
        "year_opts": _student_year_options(),
        "students": students,
        "staff": staff,
        "tag": tags,
    }
    return render(request, "admin/users_directory.html", context)

def create_staff(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Staff account '{user.username}' created.")
            return redirect("users_directory")
    else:
        form = CustomUserCreationForm()
    return render(request, "admin/create_staff.html", {"form": form})

@staff_member_required
def admin_create_student(request):
    if request.method == "POST":
        form = AdminCreateStudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Student created and tag assigned (if selected).")
            return redirect(reverse("admin_create_student"))
    else:
        form = AdminCreateStudentForm()
    return render(request, "admin/admin_create_student.html", {"form": form})

@staff_member_required
def attendance_list(request):
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    college = (request.GET.get("college") or "").strip()
    teacher_id = (request.GET.get("teacher") or "").strip()
    section_id = (request.GET.get("course_info") or "").strip()
    device_id = (request.GET.get("device_id") or "").strip()
    start = (request.GET.get("start") or "").strip()
    end = (request.GET.get("end") or "").strip()
    order = (request.GET.get("order") or "-session_date").strip()

    qs = Attendance.objects.select_related(
        "student", "course_info", "course_info__course", "course_info__teacher"
    )

    if q:
        qs = qs.filter(
            Q(student__username__icontains=q) |
            Q(student__first_name__icontains=q) |
            Q(student__last_name__icontains=q) |
            Q(student__custom_id__icontains=q) |
            Q(student__email__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if college:
        qs = qs.filter(course_info__course__college=college)
    if teacher_id:
        try:
            qs = qs.filter(course_info__teacher_id=int(teacher_id))
        except ValueError:
            pass
    if section_id:
        try:
            qs = qs.filter(course_info_id=int(section_id))
        except ValueError:
            pass
    if device_id:
        qs = qs.filter(device_id__icontains=device_id)

    start_d = _parse_date(start)
    end_d = _parse_date(end)
    if start_d:
        qs = qs.filter(session_date__gte=start_d)
    if end_d:
        qs = qs.filter(session_date__lte=end_d)

    subq = Enrollment.objects.filter(
        student_id=OuterRef("student_id"),
        course_info_id=OuterRef("course_info_id"),
    ).values("attendance_warning_level")[:1]

    qs = qs.annotate(
        warn_level=Coalesce(Subquery(subq, output_field=IntegerField()), Value(0))
    )

    allowed_order = {
        "session_date", "-session_date",
        "first_seen", "-first_seen",
        "status", "-status",
        "student__username", "-student__username",
        "course_info__course__code", "-course_info__course__code",
        "course_info__class_name", "-course_info__class_name",
    }
    if order not in allowed_order:
        order = "-session_date"

    records = qs.order_by(order)[:1000]

    teacher_opts = (
        User.objects.filter(role="teacher")
        .order_by("first_name", "last_name", "username")
        .values("id", "first_name", "last_name", "username")
    )
    section_opts = list(
        CourseInfo.objects
        .select_related("course", "teacher")
        .order_by("course__code", "class_name")
        .values(
            "id", "class_name", "course__code", "course__name",
            "teacher__username", "teacher__first_name", "teacher__last_name"
        )
    )

    context = {
        "records": records,
        "q": q,
        "status": status,
        "college": college,
        "teacher_id": teacher_id,
        "section_id": section_id,
        "device_id": device_id,
        "start": start,
        "end": end,
        "order": order,
        "status_opts": Attendance.STATUS_CHOICES,
        "college_opts": Course.COLLEGE_CHOICES,
        "teacher_opts": teacher_opts,
        "section_opts": section_opts,
    }
    return render(request, "admin/attendance_list.html", context)

@staff_member_required
def registration_control(request):
    effective = is_registration_open()
    override = cache.get("registration:is_open")

    if request.method == "POST":
        val = request.POST.get("is_open")
        if val == "clear":
            cache.delete("registration:is_open")
            messages.success(request, "Override cleared — using settings/date window now.")
        else:
            is_open = (val == "1")
            cache.set("registration:is_open", is_open, timeout=None)
            messages.success(request, f"Add/Drop is now forced to {'OPEN' if is_open else 'CLOSED'}.")
        return redirect("registration_control")

    return render(request, "admin/registration_control.html", {
        "effective": effective,
        "override": override,
    })
