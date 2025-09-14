from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator


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
        ('admin', 'Administration'),
    ]

    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    college = models.CharField(max_length=100, choices=COLLEGE_CHOICES)
    custom_id = models.CharField(max_length=50, unique=True, db_index=True)

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
    section = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
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
                fields=['course', 'year', 'semester', 'section'],
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

    attendance_warning_level = models.PositiveSmallIntegerField(default=0) 
    failed_due_to_attendance = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['course_info', 'student'],
                name='unique_student_per_section'
            ),
        ]




class RFIDTag(models.Model):
    tag_uid = models.CharField(max_length=100, unique=True, db_index=True)
    assigned_to = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        to_field='custom_id',               
        db_column='assigned_to_custom_id',  
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rfid_tag'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        who = self.assigned_to.username if self.assigned_to else "unassigned"
        return f"{self.tag_uid} -> {who}"


class RfidScan(models.Model):
    uid = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="rfid_scans",
    )
    tag = models.ForeignKey(
        "main_app.RFIDTag",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="rfid_scans",
    )
    device_id = models.CharField(max_length=64, blank=True, null=True)
    source_ip = models.GenericIPAddressField(blank=True, null=True)
    status = models.CharField(max_length=10, default="SCAN")  # IN / OUT / SCAN
    success = models.BooleanField(default=False)
    note = models.TextField(blank=True, null=True)
    extra = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        local_ts = timezone.localtime(self.created_at)
        who = self.user.username if self.user else "unknown"
        return f"{self.uid} ({who}) @ {local_ts.strftime('%Y-%m-%d %H:%M:%S')}"
    


class Attendance(models.Model):
    STATUS_CHOICES = [
        ("PRESENT", "Present"),
        ("ABSENT", "Absent"),
        ("LATE", "Late"),
    ]

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    course_info = models.ForeignKey(    
        "main_app.CourseInfo",
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    session_date = models.DateField()   
    first_seen = models.DateTimeField() 
    last_seen = models.DateTimeField()   
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PRESENT")
    scans = models.ManyToManyField(RfidScan, blank=True, related_name="attendance_links")
    device_id = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("student", "course_info", "session_date")]
        ordering = ["-session_date", "-first_seen"]

    def __str__(self):
        return f"{self.student} / {self.course_info} / {self.session_date} → {self.status}"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.jpg')
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
