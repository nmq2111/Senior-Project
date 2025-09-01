# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator

# ---------- Serializable default helpers ----------
def current_year():
    return timezone.now().year

def today_local():
    return timezone.localdate()

def now_local_time():
    return timezone.localtime().time()



class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]
    COLLEGE_CHOICES = [
        ('arts_science', 'College of Arts & Science'),
        ('business_finance', 'College of Business & Finance'),
        ('engineering', 'College of Engineering'),
        ('it', 'College of Information Technology'),
        ('medical_health', 'College of Medical & Health Sciences'),
        ('admin', 'Admin'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    college = models.CharField(max_length=100, choices=COLLEGE_CHOICES)
    custom_id = models.CharField(max_length=9, unique=True, blank=True, null=True)  # e.g., S20250001

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.custom_id:
            year = timezone.now().year
            prefix = {'student': 'S', 'teacher': 'T', 'admin': 'A'}.get(self.role, 'X')
            number_part = f"{self.id:04d}"
            self.custom_id = f"{prefix}{year}{number_part}"
            super().save(update_fields=['custom_id'])

    def __str__(self):
        return f"{self.username} ({self.custom_id or 'no-id'})"



class Course(models.Model):
    COLLEGE_CHOICES = [
        ('arts_science', 'College of Arts & Science'),
        ('business_finance', 'College of Business & Finance'),
        ('engineering', 'College of Engineering'),
        ('it', 'College of Information Technology'),
        ('medical_health', 'College of Medical & Health Sciences'),
        ('general', 'General'),
    ]

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    college = models.CharField(max_length=100, choices=COLLEGE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.code})"


class CourseInfo(models.Model):
    SEMESTER_CHOICES = [
        ('first', 'First'),
        ('second', 'Second'),
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

    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='sections')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='teaching_sections'
    )
    year = models.PositiveIntegerField(default=current_year)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    class_name = models.CharField(max_length=100)
    capacity = models.PositiveIntegerField(validators=[MinValueValidator(5)])
    session_type = models.CharField(max_length=10, choices=SESSION_TYPE_CHOICES)
    days = models.CharField(max_length=3, choices=DAYS_CHOICES)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name='courseinfo_end_after_start'
            ),
            models.UniqueConstraint(
                fields=['course', 'teacher', 'year', 'semester', 'class_name'],
                name='unique_section_per_term_teacher'
            ),
        ]

    def get_duration_minutes(self):
        return 50 if self.session_type == 'lecture' else 100

    @property
    def is_full(self):
        return self.enrollments.count() >= self.capacity

    def __str__(self):
        return f"{self.course.code} – {self.get_session_type_display()} {self.class_name} ({self.get_days_display()})"



class Enrollment(models.Model):
    course_info = models.ForeignKey(CourseInfo, on_delete=models.CASCADE, related_name='enrollments')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'student'},
        related_name='enrollments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['course_info', 'student'],
                name='unique_student_per_section'
            ),
        ]

    @property
    def course(self):
        return self.course_info.course

    def __str__(self):
        full_name = f"{self.student.first_name} {self.student.last_name}".strip() or self.student.username
        return f"{full_name} – {self.course.code} ({self.course_info.class_name})"



class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ]

    tag = models.ForeignKey('RFIDTag', on_delete=models.SET_NULL, null=True, blank=True, related_name='records')
    uid = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    scanned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="SCAN")
    device_id = models.CharField(max_length=100, blank=True, null=True)  
    source_ip = models.GenericIPAddressField(blank=True, null=True)
    success = models.BooleanField(default=True)
    note = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['uid', 'scanned_at']),
        ]
        ordering = ['-scanned_at']

    def __str__(self):
        who = self.user.username if self.user else "unknown-user"
        return f"{self.scanned_at:%Y-%m-%d %H:%M:%S} | {self.uid} -> {who} [{self.status}]"



class RFIDTag(models.Model):
    tag_uid = models.CharField(max_length=100, unique=True, db_index=True)
    assigned_to = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rfid_tag'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.assigned_to.username if self.assigned_to else "unassigned"
        return f"{self.tag_uid} -> {who}"


class RfidScan(models.Model):
    uid = models.CharField(max_length=100, db_index=True)
    device_id = models.CharField(max_length=64, blank=True, null=True)
    extra = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        local_ts = timezone.localtime(self.created_at)
        return f"{self.uid} @ {local_ts.strftime('%Y-%m-%d %H:%M:%S')}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.jpg')
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
