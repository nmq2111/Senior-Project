from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from ..models import Course, CourseInfo, Enrollment
from ..forms import CourseForm, CourseInfoForm
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from datetime import datetime

User = get_user_model()

MAX_COURSES_PER_STUDENT = 6

# === Helpers ===
def _parse_dt(s):
    if not s:
        return None
    try:
        return timezone.make_aware(datetime.fromisoformat(s))
    except Exception:
        return None

def _times_overlap(a_start, a_end, b_start, b_end):
    return (a_start < b_end) and (a_end > b_start)

def is_registration_open():
    cfg = getattr(settings, "REGISTRATION_CONTROL", {})
    default_open = bool(cfg.get("DEFAULT_OPEN", True))
    open_from = _parse_dt(cfg.get("OPEN_FROM"))
    open_until = _parse_dt(cfg.get("OPEN_UNTIL"))
    override = cache.get("registration:is_open")
    if override is not None:
        return bool(override)
    now = timezone.now()
    if open_from and now < open_from:
        return False
    if open_until and now > open_until:
        return False
    return default_open


# === Views ===
@login_required
def courses_list(request):
    q = (request.GET.get("q") or "").strip()
    college = (request.GET.get("college") or "").strip()
    order = (request.GET.get("order") or "code").strip()

    qs = Course.objects.all()
    if college:
        qs = qs.filter(college=college)
    if q:
        qs = qs.filter(Q(code__icontains=q) | Q(name__icontains=q))

    if order not in {"code", "-code", "name", "-name"}:
        order = "code"
    courses = qs.order_by(order)

    return render(
        request,
        "courses/courses_list.html",
        {
            "courses": courses,
            "q": q,
            "college": college,
            "order": order,
            "college_opts": Course.COLLEGE_CHOICES,
        },
    )

class CourseCreate(LoginRequiredMixin, CreateView):
    model = Course
    form_class = CourseForm
    template_name = "courses/course_form.html"
    success_url = reverse_lazy("courses_list")

class CourseEdit(LoginRequiredMixin, UpdateView):
    model = Course
    fields = ["name", "code", "college"]
    template_name = "courses/course_form.html"
    success_url = reverse_lazy("courses_list")

class CourseDelete(LoginRequiredMixin, DeleteView):
    model = Course
    template_name = "courses/course_confirm_delete.html"
    success_url = reverse_lazy("courses_list")

@login_required
def courseInfo_list(request):
    q = (request.GET.get("q") or "").strip()
    college = (request.GET.get("college") or "").strip()
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    section = (request.GET.get("section") or "").strip()
    status = (request.GET.get("status") or "").strip()
    days = (request.GET.get("days") or "").strip()
    session_type = (request.GET.get("session_type") or "").strip()
    teacher_id = (request.GET.get("teacher") or "").strip()
    available_only = request.GET.get("available_only") == "1"
    order = (request.GET.get("order") or "course__code").strip()

    qs = (
        CourseInfo.objects
        .select_related("course", "teacher")
        .annotate(enrolled_count=Count("enrollments"))
    )

    if q:
        qs = qs.filter(
            Q(course__code__icontains=q) |
            Q(course__name__icontains=q) |
            Q(class_name__icontains=q)
        )
    if college:
        qs = qs.filter(course__college=college)
    if year:
        try:
            qs = qs.filter(year=int(year))
        except ValueError:
            pass
    if semester:
        qs = qs.filter(semester=semester)
    if section:
        try:
            qs = qs.filter(section=int(section))
        except ValueError:
            pass
    if status:
        qs = qs.filter(status=status)
    if days:
        qs = qs.filter(days=days)
    if session_type:
        qs = qs.filter(session_type=session_type)
    if teacher_id:
        try:
            qs = qs.filter(teacher__id=int(teacher_id))
        except ValueError:
            pass
    if available_only:
        qs = qs.filter(status="Yes").filter(enrolled_count__lt=F("capacity"))

    allowed_order = {
        "course__code", "-course__code",
        "course__name", "-course__name",
        "class_name", "-class_name",
        "section", "-section",
        "start_time", "-start_time",
        "year", "-year",
        "semester", "-semester",
        "teacher__username", "-teacher__username",
    }
    if order not in allowed_order:
        order = "course__code"
    sections = qs.order_by(order)

    teacher_opts = list(
        User.objects.filter(role="teacher")
        .order_by("first_name", "last_name", "username")
        .values("id", "first_name", "last_name", "username")
    )
    year_opts = list(
        CourseInfo.objects.order_by("-year").values_list("year", flat=True).distinct()
    )

    context = {
        "sections": sections,
        "q": q,
        "college": college,
        "year": year,
        "semester": semester,
        "status": status,
        "days": days,
        "session_type": session_type,
        "teacher_id": teacher_id,
        "available_only": available_only,
        "order": order,
        "college_opts": Course.COLLEGE_CHOICES,
        "semester_opts": CourseInfo.SEMESTER_CHOICES,
        "status_opts": CourseInfo.STATUS_CHOICES,
        "days_opts": CourseInfo.DAYS_CHOICES,
        "session_type_opts": CourseInfo.SESSION_TYPE_CHOICES,
        "teacher_opts": teacher_opts,
        "year_opts": year_opts,
    }
    return render(request, "courses/course_Info/courseInfo_list.html", context)

@login_required
def courseInfo_detail(request, pk):
    course = get_object_or_404(CourseInfo, id=pk)
    return render(request, "courses/course_Info/courseInfo_detail.html", {"course": course})

class CourseInfoCreate(LoginRequiredMixin, CreateView):
    model = CourseInfo
    form_class = CourseInfoForm
    template_name = "courses/course_Info/courseInfo_form.html"
    success_url = reverse_lazy("courseInfo_list")

class CourseInfoEdit(LoginRequiredMixin, UpdateView):
    model = CourseInfo
    fields = [
        "course", "teacher", "year", "semester", "class_name", "capacity",
        "session_type", "days", "status", "start_time", "end_time",
    ]
    template_name = "courses/course_Info/courseInfo_form.html"

    def get_success_url(self):
        return reverse("courseInfo_detail", args=[self.object.pk])

class CourseInfoDelete(LoginRequiredMixin, DeleteView):
    model = CourseInfo
    template_name = "courses/course_Info/courseInfo_confirm_delete.html"
    success_url = reverse_lazy("courseInfo_list")

@login_required
def register_course(request):
    user = request.user
    if user.role != "student":
        messages.error(request, "Only students can register for courses.")
        return redirect("home")

    reg_open = is_registration_open()

    enrolled_qs = (
        Enrollment.objects
        .filter(student=user)
        .select_related("course_info", "course_info__course", "course_info__teacher")
    )
    enrolled = list(enrolled_qs)
    enrolled_courseinfo_ids = [e.course_info_id for e in enrolled]
    enrolled_term_course_keys = {
        (e.course_info.course_id, e.course_info.year, e.course_info.semester) for e in enrolled
    }

    enrolled_by_term = {}
    for e in enrolled:
        key = (e.course_info.year, e.course_info.semester)
        enrolled_by_term.setdefault(key, []).append(e.course_info)

    q = (request.GET.get("q") or "").strip()
    college = (request.GET.get("college") or "").strip()
    year = (request.GET.get("year") or "").strip()
    semester = (request.GET.get("semester") or "").strip()
    days = (request.GET.get("days") or "").strip()
    session_type = (request.GET.get("session_type") or "").strip()
    teacher_id = (request.GET.get("teacher") or "").strip()
    order = (request.GET.get("order") or "course__code,section").strip()

    qs = (
        CourseInfo.objects
        .select_related("course", "teacher")
        .annotate(enrolled_count=Count("enrollments"))
        .exclude(id__in=enrolled_courseinfo_ids)
        .filter(course__college__in=[user.college, "general"])
        .filter(status__in=["Yes", "Available"])
        .filter(enrolled_count__lt=F("capacity"))
    )

    if q:
        qs = qs.filter(
            Q(course__code__icontains=q) |
            Q(course__name__icontains=q) |
            Q(class_name__icontains=q) |
            Q(teacher__username__icontains=q) |
            Q(teacher__first_name__icontains=q) |
            Q(teacher__last_name__icontains=q)
        )
    if college:
        qs = qs.filter(course__college=college)
    if year:
        try:
            qs = qs.filter(year=int(year))
        except ValueError:
            pass
    if semester:
        qs = qs.filter(semester=semester)
    if days:
        qs = qs.filter(days=days)
    if session_type:
        qs = qs.filter(session_type=session_type)
    if teacher_id:
        try:
            qs = qs.filter(teacher__id=int(teacher_id))
        except ValueError:
            pass

    allowed = {
        "course__code", "-course__code",
        "course__name", "-course__name",
        "section", "-section",
        "class_name", "-class_name",
        "teacher__username", "-teacher__username",
        "start_time", "-start_time",
        "year", "-year",
        "semester", "-semester",
    }
    order_by = []
    for part in [p.strip() for p in order.split(",") if p.strip()]:
        order_by.append(part if part in allowed else "course__code")
    if not order_by:
        order_by = ["course__code", "section"]

    available_courses = list(qs.order_by(*order_by))
    for ci in available_courses:
        ci._duplicate_course_term = (ci.course_id, ci.year, ci.semester) in enrolled_term_course_keys
        term_key = (ci.year, ci.semester)
        ci._time_clash = False
        if term_key in enrolled_by_term:
            for other in enrolled_by_term[term_key]:
                if other.days == ci.days and _times_overlap(ci.start_time, ci.end_time, other.start_time, other.end_time):
                    ci._time_clash = True
                    break
        reasons = []
        if ci._duplicate_course_term:
            reasons.append("Already registered in this course this term")
        if ci._time_clash:
            reasons.append("Time clash with your schedule")
        ci._block_reason = " · ".join(reasons)

    if request.method == "POST":
        if not reg_open:
            messages.warning(request, "Add/Drop period is closed.")
            return redirect("register_course")

        course_info_id = request.POST.get("course_info_id")
        ci = get_object_or_404(CourseInfo, id=course_info_id)

        if ci.course.college not in (user.college, "general"):
            messages.warning(request, "This section is not in your college.")
            return redirect("register_course")
        if ci.status not in ("Yes", "Available") or ci.enrollments.count() >= ci.capacity:
            messages.warning(request, "This section is not available.")
            return redirect("register_course")

        if Enrollment.objects.filter(student=user).count() >= MAX_COURSES_PER_STUDENT:
            messages.error(request, "You reached the maximum number of courses.")
            return redirect("register_course")

        if Enrollment.objects.filter(student=user, course_info=ci).exists():
            messages.warning(request, "You are already registered in this section.")
            return redirect("register_course")

        if Enrollment.objects.filter(
            student=user,
            course_info__course_id=ci.course_id,
            course_info__year=ci.year,
            course_info__semester=ci.semester,
        ).exists():
            messages.warning(request, "You already have a section of this course for this term.")
            return redirect("register_course")

        clashes = Enrollment.objects.filter(
            student=user,
            course_info__year=ci.year,
            course_info__semester=ci.semester,
            course_info__days=ci.days,
            course_info__start_time__lt=ci.end_time,
            course_info__end_time__gt=ci.start_time,
        ).exists()
        if clashes:
            messages.warning(request, "This section conflicts with another registered section.")
            return redirect("register_course")

        Enrollment.objects.create(student=user, course_info=ci)
        messages.success(
            request,
            f"Registered: {ci.course.code} (Section {getattr(ci, 'section', '—')}) — "
            f"{ci.get_days_display()} {ci.start_time.strftime('%H:%M')}–{ci.end_time.strftime('%H:%M')}"
        )
        return redirect("register_course")

    teacher_opts = list(
        User.objects.filter(role="teacher")
        .order_by("first_name", "last_name", "username")
        .values("id", "first_name", "last_name", "username")
    )
    year_opts = list(
        CourseInfo.objects.order_by("-year").values_list("year", flat=True).distinct()
    )

    context = {
        "available_courses": available_courses,
        "registered_courses": enrolled,
        "q": q,
        "college": college,
        "year": year,
        "semester": semester,
        "days": days,
        "session_type": session_type,
        "teacher_id": teacher_id,
        "order": ",".join(order_by),
        "max_courses": MAX_COURSES_PER_STUDENT,
        "college_opts": Course.COLLEGE_CHOICES,
        "semester_opts": CourseInfo.SEMESTER_CHOICES,
        "days_opts": CourseInfo.DAYS_CHOICES,
        "session_type_opts": CourseInfo.SESSION_TYPE_CHOICES,
        "teacher_opts": teacher_opts,
        "year_opts": year_opts,
        "reg_open": reg_open,
    }
    return render(request, "courses/register.html", context)

@login_required
def drop_course(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
    if request.method == "POST":
        enrollment.delete()
    return redirect("register_course")
