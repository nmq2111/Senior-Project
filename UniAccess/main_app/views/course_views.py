from django.urls import reverse , reverse_lazy
from django.views.generic.edit import CreateView , UpdateView , DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404 , render

from ..models import Course , CourseInfo , CourseRegistration
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

    
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return HttpResponseForbidden("Only admins can add courses.")
        return super().dispatch(request, *args, **kwargs)




class CourseEdit(LoginRequiredMixin , UpdateView):
    model = Course
    fields = ['name', 'code', 'college' ]
    template_name = 'courses/course_form.html' 
    
    def get_success_url(self):
        return reverse('course_detail', args=[self.object.pk])
    

    
    def dispatch(self, request, *args, **kwargs):
     if request.user.role != 'admin':
        return HttpResponseForbidden("Only admins can edit courses.")
     return super().dispatch(request, *args, **kwargs)



class CourseDelete(LoginRequiredMixin , DeleteView):
    model = Course
    template_name = 'courses/course_confirm_delete.html' 
    success_url = reverse_lazy('courses_list')


    def dispatch(self, request, *args, **kwargs):
     if request.user.role != 'admin':
        return HttpResponseForbidden("Only admins can delete courses.")
     return super().dispatch(request, *args, **kwargs)
    





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
    
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.role != 'admin':
            return HttpResponseForbidden("Only admins can add courses.")
        return super().dispatch(request, *args, **kwargs)




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
            'status'
        ]
    template_name = 'courses/course_Info/courseInfo_form.html' 
    
    def get_success_url(self):
        return reverse('courseInfo_detail', args=[self.object.pk])
    

    
    def dispatch(self, request, *args, **kwargs):
     if request.user.role != 'admin':
        return HttpResponseForbidden("Only admins can edit courses.")
     return super().dispatch(request, *args, **kwargs)



class CourseInfoDelete(LoginRequiredMixin , DeleteView):
    model = CourseInfo
    template_name = 'courses/course_Info/courseInfo_confirm_delete.html' 
    success_url = reverse_lazy('courseInfo_list')


    def dispatch(self, request, *args, **kwargs):
     if request.user.role != 'admin':
        return HttpResponseForbidden("Only admins can delete courses.")
     return super().dispatch(request, *args, **kwargs)
    


@login_required
def available_courses(request):
    if request.user.role != 'student':
        return redirect('home')

    # Limit to non-full courses and exclude ones already registered by the student
    registered_courses = CourseRegistration.objects.filter(student=request.user).values_list('course_id', flat=True)
    available = Course.objects.exclude(id__in=registered_courses).filter(capacity__gt=models.F('registration__count'))

    return render(request, 'courses/available_courses.html', {
        'available_courses': available,
        'current_count': CourseRegistration.objects.filter(student=request.user).count()
    })