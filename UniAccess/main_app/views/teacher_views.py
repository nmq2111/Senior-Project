# main_app/views/teacher_views.py
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Max, F, Case, When, Value, FloatField
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic.edit import UpdateView
from main_app.models import Attendance, CourseInfo, Enrollment
from django.db.models.expressions import ExpressionWrapper


from django.contrib.auth import get_user_model


User = get_user_model()




def _is_teacher(user):
    return getattr(user, "role", None) == "teacher" or user.is_staff or user.is_superuser


@login_required
def attendance_take_C(request):
    user = request.user
    if not _is_teacher(user):
        return HttpResponseForbidden("Teachers only.")

    # --- Top "Take Attendance" date ---
    date_str = (request.GET.get("date") or "").strip()
    if date_str:
        try:
            session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            session_date = timezone.localdate()
            messages.warning(request, "Invalid date; using today.")
    else:
        session_date = timezone.localdate()

    # ---------- existing filters (unchanged) ----------
    q          = (request.GET.get("q") or "").strip()
    status     = (request.GET.get("status") or "").strip()
    section_id = (request.GET.get("course_info") or "").strip()
    start      = (request.GET.get("start") or "").strip()
    end        = (request.GET.get("end") or "").strip()
    order      = (request.GET.get("order") or "-session_date").strip()

    qs = (
        Attendance.objects
        .select_related("student", "course_info", "course_info__course", "course_info__teacher")
    )
    if not (user.is_staff or user.is_superuser):
        qs = qs.filter(course_info__teacher=user)

    if q:
        qs = qs.filter(
            Q(student__username__icontains=q) |
            Q(student__first_name__icontains=q) |
            Q(student__last_name__icontains=q) |
            Q(student__custom_id__icontains=q) |
            Q(student__email__icontains=q) |
            Q(course_info__course__code__icontains=q) |
            Q(course_info__course__name__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if section_id:
        try:
            qs = qs.filter(course_info_id=int(section_id))
        except ValueError:
            pass

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

    # ---------- Sections for the top panel ----------
    section_qs = CourseInfo.objects.select_related("course", "teacher")
    if not (user.is_staff or user.is_superuser):
        section_qs = section_qs.filter(teacher=user)

    # for the filters (unchanged)
    section_opts = list(
        section_qs.order_by("course__code", "class_name").values(
            "id", "class_name",
            "course__code", "course__name",
            "teacher__username", "teacher__first_name", "teacher__last_name"
        )
    )

    # for the top "group by course" panel
    teacher_sections = section_qs.order_by("course__code", "section", "class_name")

    context = {
        # top panel
        "session_date": session_date,
        "teacher_sections": teacher_sections,

        # table + filters
        "records": records,
        "q": q, "status": status,
        "section_id": section_id,
        "start": start, "end": end,
        "order": order,
        "status_opts": Attendance.STATUS_CHOICES,
        "section_opts": section_opts,
    }
    return render(request, "teacher/attendance_take_C.html", context)
    


@login_required
def teacher_attendance_list(request):
    user = request.user
    if not _is_teacher(user):
        return HttpResponseForbidden("Teachers only.")

    # --- Top "Take Attendance" date ---
    date_str = (request.GET.get("date") or "").strip()
    if date_str:
        try:
            session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception:
            session_date = timezone.localdate()
            messages.warning(request, "Invalid date; using today.")
    else:
        session_date = timezone.localdate()

    # ---------- existing filters (unchanged) ----------
    q          = (request.GET.get("q") or "").strip()
    status     = (request.GET.get("status") or "").strip()
    section_id = (request.GET.get("course_info") or "").strip()
    start      = (request.GET.get("start") or "").strip()
    end        = (request.GET.get("end") or "").strip()
    order      = (request.GET.get("order") or "-session_date").strip()

    qs = (
        Attendance.objects
        .select_related("student", "course_info", "course_info__course", "course_info__teacher")
    )
    if not (user.is_staff or user.is_superuser):
        qs = qs.filter(course_info__teacher=user)

    if q:
        qs = qs.filter(
            Q(student__username__icontains=q) |
            Q(student__first_name__icontains=q) |
            Q(student__last_name__icontains=q) |
            Q(student__custom_id__icontains=q) |
            Q(student__email__icontains=q) |
            Q(course_info__course__code__icontains=q) |
            Q(course_info__course__name__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    if section_id:
        try:
            qs = qs.filter(course_info_id=int(section_id))
        except ValueError:
            pass

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

    # ---------- Sections for the top panel ----------
    section_qs = CourseInfo.objects.select_related("course", "teacher")
    if not (user.is_staff or user.is_superuser):
        section_qs = section_qs.filter(teacher=user)

    # for the filters (unchanged)
    section_opts = list(
        section_qs.order_by("course__code", "class_name").values(
            "id", "class_name",
            "course__code", "course__name",
            "teacher__username", "teacher__first_name", "teacher__last_name"
        )
    )

    # for the top "group by course" panel
    teacher_sections = section_qs.order_by("course__code", "section", "class_name")

    context = {
        # top panel
        "session_date": session_date,
        "teacher_sections": teacher_sections,

        # table + filters
        "records": records,
        "q": q, "status": status,
        "section_id": section_id,
        "start": start, "end": end,
        "order": order,
        "status_opts": Attendance.STATUS_CHOICES,
        "section_opts": section_opts,
    }
    return render(request, "teacher/attendance_list.html", context)


@login_required
def teacher_take_attendance(request, course_info_id: int):
    """
    Bulk take/edit attendance for a single section and date.
    Only teacher assigned to that CourseInfo (or staff) can access.
    """
    user = request.user
    ci = get_object_or_404(CourseInfo.objects.select_related("course", "teacher"), id=course_info_id)

    if not (user.is_staff or user.is_superuser) and ci.teacher_id != user.id:
        return HttpResponseForbidden("You do not teach this section.")

    # Pick session date (default today)
    session_date_str = (request.GET.get("date") or request.POST.get("date") or "").strip()
    if session_date_str:
        try:
            session_date = datetime.strptime(session_date_str, "%Y-%m-%d").date()
        except Exception:
            session_date = timezone.localdate()
            messages.warning(request, "Invalid date; using today.")
    else:
        session_date = timezone.localdate()

    # Get enrolled students
    enrollments = (
        Enrollment.objects
        .filter(course_info=ci)
        .select_related("student")
        .order_by("student__first_name", "student__last_name", "student__username")
    )

    # Map existing attendance for that date
    existing = {
        a.student_id: a
        for a in Attendance.objects.filter(course_info=ci, session_date=session_date)
    }

    if request.method == "POST":
        changed = 0
        for e in enrollments:
            field = f"status_{e.student_id}"
            val = (request.POST.get(field) or "").upper()
            if val not in {"PRESENT", "LATE", "ABSENT"}:
                continue

            att = existing.get(e.student_id)
            if att is None:
                # create with sensible defaults
                start_dt = timezone.make_aware(datetime.combine(session_date, ci.start_time))
                end_dt   = timezone.make_aware(datetime.combine(session_date, ci.end_time))
                att = Attendance(
                    student=e.student,
                    course_info=ci,
                    session_date=session_date,
                    first_seen=start_dt,
                    last_seen=end_dt,
                    status=val,
                )
            else:
                att.status = val
                # keep first/last seen as-is; teacher can edit in single edit view if needed

            att.device_id = att.device_id or "TEACHER-MARK"
            att.save()
            existing[e.student_id] = att
            changed += 1

        messages.success(request, f"Attendance saved for {session_date} (updated {changed} rows).")
        # redirect to same page to avoid resubmits
        return HttpResponseRedirect(
            reverse("teacher_take_attendance", args=[ci.id]) + f"?date={session_date.isoformat()}"
        )

    context = {
        "ci": ci,
        "session_date": session_date,
        "enrollments": enrollments,
        "existing": existing,  # dict student_id -> Attendance
        "status_choices": Attendance.STATUS_CHOICES,
    }
    return render(request, "teacher/take_attendance.html", context)


class TeacherAttendanceEdit(LoginRequiredMixin, UpdateView):
    model = Attendance
    fields = ["status", "first_seen", "last_seen", "device_id"]
    template_name = "teacher/attendance_edit.html"

    def dispatch(self, request, *args, **kwargs):
        # Restrict edit to teacher’s own section unless staff
        self.object = self.get_object()
        user = request.user
        if not (user.is_staff or user.is_superuser):
            if getattr(self.object.course_info, "teacher_id", None) != user.id:
                return HttpResponseForbidden("You cannot edit this record.")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        # back to section/date view if referer contains it; otherwise teacher list
        ref = self.request.META.get("HTTP_REFERER")
        return ref or reverse_lazy("teacher_attendance_list")


def _is_teacher(user):
    return getattr(user, "role", None) == "teacher" or user.is_staff or user.is_superuser

@login_required
def teacher_userbase(request,  course_info_id=None):
    """
    Directory-style list of ONLY the students enrolled in sections taught by this teacher.
    Filters: q, college, year. Sorted by username by default.
    """
    user = request.user
    if not _is_teacher(user):
        return HttpResponseForbidden("Teachers only.")

    # All sections this teacher teaches
    section_ids = list(
        CourseInfo.objects.filter(teacher=user).values_list("id", flat=True)
    )
    if not section_ids:
        # no sections → empty list
        students = User.objects.none()
        year_opts = []
    else:
        # Students enrolled in any of those sections
        student_ids = (
            Enrollment.objects.filter(course_info_id__in=section_ids)
            .values_list("student_id", flat=True)
            .distinct()
        )
        students = User.objects.filter(id__in=student_ids, role="student")

    # ---- Filters ----
    q = (request.GET.get("q") or "").strip()
    college = (request.GET.get("college") or "").strip()
    year = (request.GET.get("year") or "").strip()
    order = (request.GET.get("order") or "username").strip()

    if q:
        students = students.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(custom_id__icontains=q)
            | Q(email__icontains=q)
        )
    if college:
        students = students.filter(college=college)
    if year:
        try:
            y = int(year)
            students = students.filter(date_joined__year=y)
        except ValueError:
            pass

    allowed_order = {"username","-username","first_name","-first_name","last_name","-last_name",
                     "custom_id","-custom_id","email","-email","date_joined","-date_joined"}
    if order not in allowed_order:
        order = "username"
    students = students.order_by(order, "username")

    # Year options based on THIS teacher’s student set
    year_opts = (
        User.objects.filter(id__in=students.values_list("id", flat=True))
        .dates("date_joined", "year", order="DESC")
    )

    ctx = {
        "q": q,
        "college": college,
        "year": year,
        "order": order,
        "college_opts": User.COLLEGE_CHOICES,
        "year_opts": [d.year for d in year_opts],
        "students": students,
        "today": timezone.localdate(),
    }
    return render(request, "teacher/users_directory.html", ctx)