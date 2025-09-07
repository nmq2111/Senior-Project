from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser , Profile , Course , CourseInfo , RFIDTag ,Attendance
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),     
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



def recent_unassigned_uids(limit=25):
    seen = set()
    out = []
    for rec in Attendance.objects.select_related('tag').order_by('-scanned_at')[:500]:
        uid = rec.uid
        if uid in seen:
            continue
        seen.add(uid)
        # skip if UID already assigned to someone
        try:
            tag = RFIDTag.objects.select_related('assigned_to').get(tag_uid=uid)
            if tag.assigned_to:  # already assigned
                continue
        except RFIDTag.DoesNotExist:
            pass
        out.append(uid)
        if len(out) >= limit:
            break
    return [(u, u) for u in out]

class AdminCreateStudentForm(UserCreationForm):
    uid_choice = forms.ChoiceField(
        required=False,
        label="Assign RFID UID (latest scans)",
        choices=[],
        help_text="Pick a recently scanned tag to assign to this student (optional)."
    )

    class Meta:
        model = User
        fields = ("username", "email")  # add anything else you need

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["uid_choice"].choices = [("", "— No tag —")] + recent_unassigned_uids()

    def save(self, commit=True):
        user = super().save(commit=commit)
        uid = self.cleaned_data.get("uid_choice")
        if uid:
            tag, _ = RFIDTag.objects.get_or_create(tag_uid=uid)
            tag.assigned_to = user
            tag.save()
        return user
