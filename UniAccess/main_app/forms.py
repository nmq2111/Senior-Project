from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser , Profile , Course , CourseInfo , RFIDTag


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



class CreateRFIDForm(UserCreationForm):
    # lock to student for this flow; change if you want
    role = forms.ChoiceField(choices=[('student','Student')], widget=forms.Select(attrs={'class':'form-select'}))
    college = forms.ChoiceField(choices=CustomUser.COLLEGE_CHOICES, widget=forms.Select(attrs={'class':'form-select'}))
    tag_uid = forms.CharField(
        label='RFID Card UID',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class':'form-control', 'placeholder':'e.g., 04:A3:1C:7B'})
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username','first_name','last_name','email','role','college','tag_uid','password1','password2')

    def clean_tag_uid(self):
        uid = (self.cleaned_data['tag_uid'] or '').strip().upper().replace(' ', '')
        if RFIDTag.objects.filter(tag_uid=uid, assigned_to__isnull=False).exists():
            raise forms.ValidationError("This UID is already assigned to another user.")
        return uid