from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser , Profile , Course , CourseInfo


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name' , 'last_name', 'email', 'role', 'college' , 'password1', 'password2')



class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'phone']


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'college']


class CourseInfoForm(forms.ModelForm):
    class Meta:
        model = CourseInfo
        fields = [
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

