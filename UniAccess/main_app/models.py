from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
        ('security', 'Security'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    photo_url = models.URLField(blank=True, null=True)

class Course(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'teacher'})

class Attendance(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'student'})
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=10, default='present')

class RFIDTag(models.Model):
    tag_uid = models.CharField(max_length=100, unique=True)
    assigned_to = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)

class AccessLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.CharField(max_length=100)  # e.g. dorm or office
    time = models.DateTimeField(auto_now_add=True)
    access_type = models.CharField(max_length=20, choices=[('entry', 'Entry'), ('exit', 'Exit')])
