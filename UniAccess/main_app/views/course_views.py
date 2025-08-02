from django.shortcuts import render
from django.urls import reverse , reverse_lazy
from django.views.generic.edit import CreateView , UpdateView , DeleteView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404

from ..models import Course
from ..forms import CourseForm



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
    fields = ['name', 'code', 'teacher' , 'year' , 'semester' , 'college' , 'class_name' , 'capacity' , 'session_type' , 'days' ]
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