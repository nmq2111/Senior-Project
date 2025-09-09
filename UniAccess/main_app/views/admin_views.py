from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Q
from ..models import Profile
from django.shortcuts import render , redirect
from ..forms import CustomUserCreationForm, AdminCreateStudentForm
from django.contrib.auth import login
from django.urls import reverse

User = get_user_model()

def _student_year_options():
    years = (
        User.objects.filter(role="student")
        .dates("date_joined", "year", order="DESC")
    )
    return [d.year for d in years]

@staff_member_required
def users_directory(request):
    q = (request.GET.get("q") or "").strip()
    college = (request.GET.get("college") or "").strip()
    year = (request.GET.get("year") or "").strip()

    students = (User.objects.filter(role="student")  .select_related("profile", "rfid_tag"))
    

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
        .filter(role__in="student")
        .select_related("tag_uid" , "profile")
        .order_by("role", "username")
    )

    context = {
        "q": q,
        "college": college,
        "year": year,
        "college_opts": User.COLLEGE_CHOICES,   # [('arts_science','...'), ...]
        "year_opts": _student_year_options(),   # [2025, 2024, ...]
        "students": students,
        "staff": staff,
        "tag" : tags,
    }
    return render(request, "admin/users_directory.html", context)

def create_staff(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.create(user=user)
            login(request, user)
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'admin/create_staff.html', {'form': form})


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




# main_app/views/admin_views.py
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import render
from datetime import datetime
from ..models import Attendance, CourseInfo, Course

User = get_user_model()

@staff_member_required
def attendance_list(request):
    q            = (request.GET.get("q") or "").strip()
    status       = (request.GET.get("status") or "").strip()
    college      = (request.GET.get("college") or "").strip()
    teacher_id   = (request.GET.get("teacher") or "").strip()
    section_id   = (request.GET.get("course_info") or "").strip()
    device_id    = (request.GET.get("device_id") or "").strip()
    start        = (request.GET.get("start") or "").strip()   # YYYY-MM-DD
    end          = (request.GET.get("end") or "").strip()     # YYYY-MM-DD
    order        = (request.GET.get("order") or "-session_date").strip()

    qs = (
        Attendance.objects
        .select_related("student", "course_info", "course_info__course", "course_info__teacher")
    )

    # ---- Filters ----
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

    # Dates are based on session_date (class day)
    def _parse_date(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            return None

    start_d = _parse_date(start)
    end_d   = _parse_date(end)
    if start_d:
        qs = qs.filter(session_date__gte=start_d)
    if end_d:
        qs = qs.filter(session_date__lte=end_d)

    # ---- Sorting (whitelist) ----
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
    records = qs.order_by(order)[:1000]  # soft cap

    # ---- Options for filters ----
    teacher_opts = (
        User.objects.filter(role="teacher")
        .order_by("first_name", "last_name", "username")
        .values("id", "first_name", "last_name", "username")
    )
    section_opts = list(
        CourseInfo.objects
        .select_related("course", "teacher")
        .order_by("course__code", "class_name")
        .values("id", "class_name", "course__code", "course__name", "teacher__username", "teacher__first_name", "teacher__last_name")
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