from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser , Profile , Course , CourseInfo , RFIDTag , RfidScan
from django.contrib.auth import get_user_model
from django.db import transaction


User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),     
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    phone = forms.CharField(
        required=True,
        max_length=20,
        label="Phone",
        widget=forms.TextInput(attrs={"placeholder": "+973 3xxxxxxx"})
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name' , 'last_name', 'email', 'role', 'college' , 'password1', 'password2')

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)  
        user.role = self.cleaned_data.get("role")
        user.college = self.cleaned_data.get("college")
        if commit:
            user.save(update_fields=["role", "college"])
        phone = self.cleaned_data.get("phone")
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.save()
    
        return user



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
    assigned_uids = set(
        RFIDTag.objects.filter(assigned_to__isnull=False)
        .values_list("tag_uid", flat=True)
    )

    seen = set()
    out = []
    for rec in RfidScan.objects.select_related("tag", "user").order_by('-created_at')[:1000]:
        uid = rec.uid
        if uid in seen:
            continue
        seen.add(uid)
        
        if uid in assigned_uids:
            continue
        
        try:
            tag = RFIDTag.objects.select_related('assigned_to').get(tag_uid=uid)
            if tag.assigned_to:  
                continue
        except RFIDTag.DoesNotExist:
            pass
        out.append(uid)
        if len(out) >= limit:
            break
    return [(u, u) for u in out]

class AdminCreateStudentForm(UserCreationForm):
    uid_choice = forms.ChoiceField(
        required=True,
        label="Assign RFID UID (latest scans)",
        choices=[],
        help_text="Pick a recently scanned tag to assign to this student (optional)."
    )

    ROLE_CHOICES = [('student', 'Student')]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

   
    phone = forms.CharField(
        required=True,
        max_length=20,
        label="Phone",
        widget=forms.TextInput(attrs={"placeholder": "+973 3xxxxxxx"})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email",
                  "password1", "password2", "role", "college")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["uid_choice"].choices = [("", "— No tag —")] + recent_unassigned_uids()
        for name in ("username", "first_name", "last_name", "email", "password1", "password2", "role", "college"):
            self.fields[name].required = True
            self.fields[name].widget.attrs["required"] = "required"

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)  
        user.role = self.cleaned_data.get("role")
        user.college = self.cleaned_data.get("college")
        if commit:
            user.save(update_fields=["role", "college"])
        phone = self.cleaned_data.get("phone")
        profile, _ = Profile.objects.get_or_create(user=user)
        profile.phone = phone
        profile.save()

        uid = self.cleaned_data.get("uid_choice")
        if uid:
            tag, _ = RFIDTag.objects.get_or_create(tag_uid=uid)
            tag.assigned_to = user
            tag.save()

        return user