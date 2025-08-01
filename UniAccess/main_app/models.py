from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from datetime import datetime  



class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    custom_id = models.CharField(max_length=9, unique=True, blank=True, null=True)

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
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'}
    )

    def __str__(self):
        return self.name


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