from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from main_app.models import CourseInfo, Enrollment, Attendance

class Command(BaseCommand):
    help = "After classes end, mark ABSENT for enrolled students who did not scan."

    def add_arguments(self, parser):
        parser.add_argument("--grace-min", type=int, default=5,
                            help="Minutes after end_time before closing a session (default 5).")

    def handle(self, *args, **opts):
        grace = opts["grace_min"]
        now = timezone.localtime()
        today = timezone.localdate()

        weekday2 = now.strftime("%a").upper()[:2]  # e.g. 'MO','TU'

        # Classes that already ended (plus grace period)
        classes = CourseInfo.objects.filter(
            status="Yes",
            days__icontains=weekday2,
            end_time__lte=(now - timedelta(minutes=grace)).time()
        )

        total_absents = 0
        for ci in classes:
            # All enrolled students
            enrolled_ids = list(Enrollment.objects.filter(courseInfo=ci).values_list("student_id", flat=True))
            if not enrolled_ids:
                continue

            # Who already has attendance today
            present_ids = set(
                Attendance.objects.filter(course_info=ci, session_date=today)
                .values_list("student_id", flat=True)
            )

            # Missing → absent
            missing = [sid for sid in enrolled_ids if sid not in present_ids]
            for sid in missing:
                Attendance.objects.get_or_create(
                    student_id=sid,
                    course_info=ci,
                    session_date=today,
                    defaults={"status": "ABSENT"}
                )
            total_absents += len(missing)

        self.stdout.write(self.style.SUCCESS(f"Marked {total_absents} students absent."))
