from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import datetime  
from django.core.validators import MinValueValidator



class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    custom_id = models.CharField(max_length=9, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.custom_id:
            year = datetime.now().year
            prefix = {
                'student': 'S',
                'teacher': 'T',
                'admin': 'A',
            }.get(self.role, 'X')
            number_part = f"{self.id:04d}"
            self.custom_id = f"{prefix}{year}{number_part}"
            super().save(update_fields=['custom_id'])

    def __str__(self):
        return f"{self.username} ({self.custom_id})"
    


class Course(models.Model):
    COLLEGE_CHOICES = [
    ('arts_science', 'College of Arts & Science'),
    ('business_finance', 'College of Business & Finance'),
    ('engineering', 'College of Engineering'),
    ('it', 'College of Information Technology'),
    ('medical_health', 'College of Medical & Health Sciences'),
    ]

    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    college  = models.CharField(max_length=100, choices=COLLEGE_CHOICES)
    

    def __str__(self):
     return f"{self.name} ({self.code})"
    


class CourseInfo(models.Model):
    SEMESTER_CHOICES = [
        ('first', 'First'),
        ('second' , 'Second'),
        ('summer', 'Summer'),
    ]

    SESSION_TYPE_CHOICES = [
        ('lecture', 'Lecture (50 min)'),
        ('lab', 'Lab (100 min)'),
    ]

    DAYS_CHOICES = [
        ('uth', 'Sunday, Tuesday, Thursday (UTH)'),
        ('mw', 'Monday, Wednesday (MW)'),
        ('fs', 'Friday, Saturday (FS) — Masters'),
    ]


    STATUS_CHOICES = [
        ('Yes', 'Available'),
        ('No', 'Not Available'),
    ]


    def current_year():
      return datetime.now().year
    

    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'}
    )
    year = models.PositiveIntegerField(default=current_year)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    class_name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(5)], 
    )
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE_CHOICES)
    days = models.CharField(max_length=3, choices=DAYS_CHOICES)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()


    def get_duration_minutes(self):
      return 50 if self.session_type == 'lecture' else 100
    
    @property
    def is_full(self):
        return self.enrollments.count() >= self.capacity
    

    def __str__(self):
     return f"{self.course.code} – {self.get_session_type_display()} on {self.get_days_display()}"
    


class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    courseInfo = models.ForeignKey(CourseInfo, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )

    def get_full_name(self):
        return f"{self.student.first_name} {self.student.last_name}"


    def __str__(self):
        return f"{self.student.get_full_name()} - {self.course.name}"
    



class Attendance(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'}
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=10, default='present')


class RFIDTag(models.Model):
    tag_uid = models.CharField(max_length=100, unique=True)
    assigned_to = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )


class AccessLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    location = models.CharField(max_length=100)  # e.g., dorm or office
    time = models.DateTimeField(auto_now_add=True)
    access_type = models.CharField(max_length=20, choices=[('entry', 'Entry'), ('exit', 'Exit')])


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.jpg')

    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"