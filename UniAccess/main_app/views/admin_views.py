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

    students = User.objects.filter(role="student")
    

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
        .select_related("tag_uid")
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