from django.utils import timezone
from django.urls import reverse, reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q , Count, F
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from ..models import Course, CourseInfo, Enrollment
from ..forms import CourseForm, CourseInfoForm
from django.contrib.auth import get_user_model


User = get_user_model()




@login_required
def courses_list(request):
    """
    Users-Directory style list:
      - search by code/name
      - filter by college
      - sort by code/name
    """
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
    q            = (request.GET.get("q") or "").strip()
    college      = (request.GET.get("college") or "").strip()
    year         = (request.GET.get("year") or "").strip()
    semester     = (request.GET.get("semester") or "").strip()
    status       = (request.GET.get("status") or "").strip()
    days         = (request.GET.get("days") or "").strip()
    session_type = (request.GET.get("session_type") or "").strip()
    teacher_id   = (request.GET.get("teacher") or "").strip()
    available_only = request.GET.get("available_only") == "1"
    order        = (request.GET.get("order") or "course__code").strip()

    qs = (
        CourseInfo.objects
        .select_related("course", "teacher")
        .annotate(enrolled_count=Count("enrollments"))
    )

    # Search
    if q:
        qs = qs.filter(
            Q(course__code__icontains=q) |
            Q(course__name__icontains=q) |
            Q(class_name__icontains=q)
        )

    # Filters
    if college:
        qs = qs.filter(course__college=college)
    if year:
        try:
            qs = qs.filter(year=int(year))
        except ValueError:
            pass
    if semester:
        qs = qs.filter(semester=semester)
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

    # Sorting (whitelist)
    allowed_order = {
        "course__code", "-course__code",
        "course__name", "-course__name",
        "class_name", "-class_name",
        "start_time", "-start_time",
        "year", "-year",
        "semester", "-semester",
        "teacher__username", "-teacher__username",
    }
    if order not in allowed_order:
        order = "course__code"
    sections = qs.order_by(order)

    # Options for filters
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


# ------------------ Registration ------------------

@login_required
def register_course(request):
    user = request.user

    if user.role != "student":
        messages.error(request, "Only students can register for courses.")
        return redirect("home")

    enrolled = Enrollment.objects.filter(student=user)
    enrolled_courseinfo_ids = enrolled.values_list("course_info__id", flat=True)

    available_courses = CourseInfo.objects.filter(status="Yes").exclude(id__in=enrolled_courseinfo_ids)

    if request.method == "POST":
        course_info_id = request.POST.get("course_info_id")
        course_info = get_object_or_404(CourseInfo, id=course_info_id)

        if enrolled.count() >= 6:
            messages.error(request, "you reached the maximum number of courses")
        elif course_info.id in enrolled_courseinfo_ids:
            messages.warning(request, "You are already registered in this course.")
        elif course_info.is_full:
            messages.warning(request, "Course is full.")
        else:
            Enrollment.objects.create(student=user, course_info=course_info)
            messages.success(request, f"Successfully registered for {course_info.course.name}")
            return redirect("register_course")

    return render(
        request,
        "courses/register.html",
        {"available_courses": available_courses, "registered_courses": enrolled},
    )


@login_required
def drop_course(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
    if request.method == "POST":
        enrollment.delete()
    return redirect("register_course")
