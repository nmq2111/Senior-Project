from django.utils import timezone
from django.urls import reverse , reverse_lazy 
from django.views.generic.edit import CreateView , UpdateView , DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404 , render , redirect
from django.contrib import messages

from ..models import Course , CourseInfo , Enrollment
from ..forms import CourseForm , CourseInfoForm 



@login_required
def courses_list(request):
    courses = Course.objects.all()
    return render(request, 'courses/courses_list.html', {'courses': courses})

@login_required
def course_detail(request , pk):
    course = get_object_or_404(Course, id=pk)
    return render(request , 'courses/course_detail.html' , {'course': course})



class CourseCreate(LoginRequiredMixin , CreateView):
    model = Course 
    form_class = CourseForm
    template_name = 'courses/course_form.html' 
    success_url = reverse_lazy('courses_list')

    
    
    def save(self, *args, **kwargs):
     if self.role == 'admin':
        self.is_staff = True
        self.is_superuser = True
     else:
        # Students and teachers can’t be superusers
        self.is_superuser = False
        # Teachers might be staff if you want them in Django Admin
        self.is_staff = (self.role == 'teacher')

     is_new = self.pk is None
     super().save(*args, **kwargs)

     if is_new and not self.custom_id:
        year = timezone.now().year
        prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A'}.get(self.role, 'X')
        number_part = f"{self.id:04d}"
        self.custom_id = f"{prefix}{year}{number_part}"
        super().save(update_fields=['custom_id'])





class CourseEdit(LoginRequiredMixin , UpdateView):
    model = Course
    fields = ['name', 'code', 'college' ]
    template_name = 'courses/course_form.html' 
    
    def get_success_url(self):
        return reverse('course_detail', args=[self.object.pk])
    

    
    def save(self, *args, **kwargs):
     if self.role == 'admin':
        self.is_staff = True
        self.is_superuser = True
     else:
        # Students and teachers can’t be superusers
        self.is_superuser = False
        # Teachers might be staff if you want them in Django Admin
        self.is_staff = (self.role == 'teacher')

     is_new = self.pk is None
     super().save(*args, **kwargs)

     if is_new and not self.custom_id:
        year = timezone.now().year
        prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A'}.get(self.role, 'X')
        number_part = f"{self.id:04d}"
        self.custom_id = f"{prefix}{year}{number_part}"
        super().save(update_fields=['custom_id'])



class CourseDelete(LoginRequiredMixin , DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html' 
    success_url = reverse_lazy('courses_list')


    def save(self, *args, **kwargs):
     if self.role == 'admin':
        self.is_staff = True
        self.is_superuser = True
     else:
        # Students and teachers can’t be superusers
        self.is_superuser = False
        # Teachers might be staff if you want them in Django Admin
        self.is_staff = (self.role == 'teacher')

     is_new = self.pk is None
     super().save(*args, **kwargs)

     if is_new and not self.custom_id:
        year = timezone.now().year
        prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A'}.get(self.role, 'X')
        number_part = f"{self.id:04d}"
        self.custom_id = f"{prefix}{year}{number_part}"
        super().save(update_fields=['custom_id'])
    





#### this is courseInfo 
@login_required
def courseInfo_list(request):
    course = CourseInfo.objects.all()
    return render(request, 'courses/course_Info/courseInfo_list.html', {'course': course})

@login_required
def courseInfo_detail(request , pk):
    course = get_object_or_404(CourseInfo, id=pk)
    return render(request , 'courses/course_Info/courseInfo_detail.html' , {'course': course})


class CourseInfoCreate(LoginRequiredMixin , CreateView):
    model = CourseInfo 
    form_class = CourseInfoForm
    template_name = 'courses/course_Info/courseInfo_form.html' 
    success_url = reverse_lazy('courseInfo_list')

    def form_valid(self, form):
       print("Form is valid")  
       return super().form_valid(form)
    

    def form_invalid(self, form):
       print("Form is INVALID:", form.errors)  
       return super().form_invalid(form)
    
    
    def save(self, *args, **kwargs):
     if self.role == 'admin':
        self.is_staff = True
        self.is_superuser = True
     else:
        # Students and teachers can’t be superusers
        self.is_superuser = False
        # Teachers might be staff if you want them in Django Admin
        self.is_staff = (self.role == 'teacher')

     is_new = self.pk is None
     super().save(*args, **kwargs)

     if is_new and not self.custom_id:
        year = timezone.now().year
        prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A'}.get(self.role, 'X')
        number_part = f"{self.id:04d}"
        self.custom_id = f"{prefix}{year}{number_part}"
        super().save(update_fields=['custom_id'])





class CourseInfoEdit(LoginRequiredMixin , UpdateView):
    model = CourseInfo
    fields = fields = [
            'course',         
            'teacher',
            'year',
            'semester',
            'class_name',
            'capacity',
            'session_type',
            'days',
            'status',
            'start_time',
            'end_time'
        ]
    template_name = 'courses/course_Info/courseInfo_form.html' 
    
    def get_success_url(self):
        return reverse('courseInfo_detail', args=[self.object.pk])
    

    
    def save(self, *args, **kwargs):
     if self.role == 'admin':
        self.is_staff = True
        self.is_superuser = True
     else:
        # Students and teachers can’t be superusers
        self.is_superuser = False
        # Teachers might be staff if you want them in Django Admin
        self.is_staff = (self.role == 'teacher')

     is_new = self.pk is None
     super().save(*args, **kwargs)

     if is_new and not self.custom_id:
        year = timezone.now().year
        prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A'}.get(self.role, 'X')
        number_part = f"{self.id:04d}"
        self.custom_id = f"{prefix}{year}{number_part}"
        super().save(update_fields=['custom_id'])



class CourseInfoDelete(LoginRequiredMixin , DeleteView):
    model = CourseInfo
    template_name = 'courses/course_Info/courseInfo_confirm_delete.html' 
    success_url = reverse_lazy('courseInfo_list')


    def save(self, *args, **kwargs):
     if self.role == 'admin':
        self.is_staff = True
        self.is_superuser = True
     else:
        # Students and teachers can’t be superusers
        self.is_superuser = False
        # Teachers might be staff if you want them in Django Admin
        self.is_staff = (self.role == 'teacher')

     is_new = self.pk is None
     super().save(*args, **kwargs)

     if is_new and not self.custom_id:
        year = timezone.now().year
        prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A'}.get(self.role, 'X')
        number_part = f"{self.id:04d}"
        self.custom_id = f"{prefix}{year}{number_part}"
        super().save(update_fields=['custom_id'])
    


@login_required
def register_course(request):
    user = request.user

    if user.role != 'student':
        messages.error(request, "Only students can register for courses.")
        return redirect('home')

    
    enrolled = Enrollment.objects.filter(student=user)
    enrolled_courseinfo_ids = enrolled.values_list('course_info__id', flat=True)

    
    available_courses = CourseInfo.objects.filter(status='Yes').exclude(id__in=enrolled_courseinfo_ids)

    if request.method == 'POST':
        course_info_id = request.POST.get('course_info_id')
        course_info = get_object_or_404(CourseInfo, id=course_info_id)

        if enrolled.count() >= 6:
            messages.error(request, "you reached the maximum number of courses")
        elif course_info.id in enrolled_courseinfo_ids:
            messages.warning(request, "You are already registered in this course.")
        elif course_info.is_full:
            messages.warning(request, "Course is full.")
        else:
            Enrollment.objects.create(
                student=user,
                course_info=course_info
            )
            messages.success(request, f"Successfully registered for {course_info.course.name}")
            return redirect('register_course')


    return render(request, 'courses/register.html', {
        'available_courses': available_courses,
        'registered_courses': enrolled,
    })

  


@login_required
def drop_course(request, enrollment_id):
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
    
    if request.method == 'POST':
        enrollment.delete()
    
    return redirect('register_course')