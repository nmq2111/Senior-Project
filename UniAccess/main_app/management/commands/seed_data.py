import random
from datetime import timedelta, time, datetime
from faker import Faker
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from main_app.models import (
    CustomUser,
    Course,
    CourseInfo,
    Enrollment,
    RFIDTag,
    RfidScan,
    Attendance,
    Profile,
)

fake = Faker() # Default locale for emails, bio, etc.

class Command(BaseCommand):
    help = "Seed realistic fake data into PostgreSQL database"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("Deleting old fake data..."))
        Attendance.objects.all().delete()
        RfidScan.objects.all().delete() 
        RFIDTag.objects.all().delete()
        Enrollment.objects.all().delete()
        CourseInfo.objects.all().delete()
        
        Profile.objects.filter(user__username__startswith="student").delete()
        Profile.objects.filter(user__username__startswith="teacher").delete()
        CustomUser.objects.filter(is_superuser=False, username__startswith="student").delete()
        CustomUser.objects.filter(is_superuser=False, username__startswith="teacher").delete()

        self.stdout.write(self.style.SUCCESS("Old data deleted."))

        # ---------------------------------------------------
        # CUSTOM REALISTIC LOCAL NAME BANKS
        # ---------------------------------------------------
        FIRST_NAMES_MALE = [
            "Ahmed", "Mohammed", "Abdullah", "Yousef", "Khalid", "Ali", "Hassan", "Hussein", 
            "Omar", "Faisal", "Salman", "Mahmood", "Saeed", "Nasser", "Ibrahim", "Tariq", 
            "Hamad", "Jassim", "Abdulrahman", "Abdulaziz", "Bader", "Isa", "Mansoor", "Zaid"
        ]
        FIRST_NAMES_FEMALE = [
            "Fatima", "Noora", "Maryam", "Aisha", "Zainab", "Huda", "Sara", "Reem", "Dana", 
            "Lulwa", "Amal", "Eman", "Basma", "Jawaher", "Maha", "Rania", "Nadia", "Layla", 
            "Hanan", "Rawan", "Hessa", "Alia", "Asma", "Noor"
        ]
        LAST_NAMES = [
            "AlQahtani", "AlKhalifa", "AlZayani", "AlDoseri", "AlMarzooq", "AlMutairi", 
            "AlHarbi", "AlSuwaidi", "AlThawadi", "AlAnsari", "AlKooheji", "AlFardan", 
            "AlGhanem", "AlHamad", "AlSayed", "AlMannai", "AlAwadhi", "AlRumaihi"
        ]

        def get_random_name():
            gender = random.choice(['male', 'female'])
            first = random.choice(FIRST_NAMES_MALE if gender == 'male' else FIRST_NAMES_FEMALE)
            last = random.choice(LAST_NAMES)
            return first, last

        # ---------------------------------------------------
        # CREATE TEACHERS
        # ---------------------------------------------------
        teachers = []
        for i in range(15):
            first, last = get_random_name()
            teacher = CustomUser.objects.create_user(
                username=f"temp_teacher_{i}",
                password="12345678",
                first_name=first,
                last_name=last,
                email=f"{first.lower()}.{last.lower()}{random.randint(10,99)}@ahlia.edu.bh",
                role="teacher",
                college=random.choice([
                    "engineering",
                    "it",
                    "business_finance",
                    "arts_science",
                    ]),
                    )
            Profile.objects.create(
                user=teacher,
                bio=f"Professor in the department of {teacher.get_college_display()}.",
                location=random.choice(["Manama", "Riffa", "Muharraq", "Isa Town"]),
                phone=f"+973{random.randint(30000000, 39999999)}",
            )
            teachers.append(teacher)

        self.stdout.write(self.style.SUCCESS(f"{len(teachers)} Teachers created."))

        # ---------------------------------------------------
        # CREATE STUDENTS
        # ---------------------------------------------------
        students = []
        for i in range(120):
            first, last = get_random_name()
            student = CustomUser.objects.create_user(
                username=f"temp_student_{i}",
                password="12345678",
                first_name=first,
                last_name=last,
                email=f"st{timezone.now().year % 100}{random.randint(1000, 9999)}@ahlia.edu.bh",
                role="student",
                college=random.choice([
                    "engineering",
                    "it",
                    "business_finance",
                    "arts_science",
                    ]),
                    )
            Profile.objects.create(
                user=student,
                bio="Undergraduate Student.",
                location=random.choice(["Manama", "Riffa", "Muharraq", "Isa Town", "Hidd", "Saar"]),
                phone=f"+973{random.randint(36000000, 39999999)}",
            )
            tag = RFIDTag.objects.create(
                tag_uid=f"HEX-{random.randint(100000, 999999):X}", # Hex formatting makes it look like a real RFID UID
                assigned_to=student,
            )
            students.append((student, tag))

        self.stdout.write(self.style.SUCCESS(f"{len(students)} Students created."))

        # ---------------------------------------------------
        # CREATE COURSE SECTIONS (WITH TIME SLOTS)
        # ---------------------------------------------------
        courses = Course.objects.all()
        if not courses.exists():
            self.stdout.write(self.style.ERROR("No courses found in database! Please add some courses first."))
            return

        # Realistic time slots dictionary
        TIME_SLOTS = {
            'lecture': [
                (time(8, 0), time(8, 50)),
                (time(9, 0), time(9, 50)),
                (time(10, 0), time(10, 50)),
                (time(11, 0), time(11, 50)),
                (time(13, 0), time(13, 50)),
                (time(14, 0), time(14, 50)),
            ],
            'lab': [
                (time(8, 0), time(9, 40)),
                (time(10, 0), time(11, 40)),
                (time(13, 0), time(14, 40)),
                (time(15, 0), time(16, 40)),
            ]
        }

        sections = []
        for course in courses:
            # Generate 1 to 2 sections per course to spread out options
            for loop_sec in range(random.randint(1, 2)):
                session_type = random.choice(["lecture", "lab"])
                chosen_slot = random.choice(TIME_SLOTS[session_type])
                days = random.choice(["mw", "uth"])
                
                current_count = CourseInfo.objects.filter(
                    course=course, year=timezone.now().year, semester="first"
                ).count()

                section = CourseInfo.objects.create(
                    course=course,
                    teacher=random.choice(teachers),
                    year=timezone.now().year,
                    semester="first",
                    section=current_count + 1,
                    class_name=f"{course.code}-S{current_count + 1}",
                    capacity=35,
                    session_type=session_type,
                    days=days,
                    status="Yes",
                    start_time=chosen_slot[0],
                    end_time=chosen_slot[1],
                )
                sections.append(section)

        self.stdout.write(self.style.SUCCESS(f"{len(sections)} Course sections created."))

        # ---------------------------------------------------
        # ENROLLMENTS (WITHOUT TIME CONFLICTS)
        # ---------------------------------------------------
        enrollments = []
        for student, tag in students:
            # Try to sign up for 4 classes, ensuring no time/day slot overlaps
            chosen_sections = []
            available_sections = list(sections)
            random.shuffle(available_sections)

            for sec in available_sections:
                if len(chosen_sections) >= random.randint(3, 5):
                    break
                
                # Conflict checking logic
                has_conflict = False
                for chosen in chosen_sections:
                    if chosen.days == sec.days:
                        # Overlap equation: (StartA < EndB) and (EndA > StartB)
                        if (sec.start_time < chosen.end_time) and (sec.end_time > chosen.start_time):
                            has_conflict = True
                            break
                
                if not has_conflict:
                    chosen_sections.append(sec)

            for section in chosen_sections:
                enrollment = Enrollment.objects.create(
                    student=student,
                    course_info=section,
                    attendance_warning_level=0,
                    failed_due_to_attendance=False,
                )
                enrollments.append((enrollment, tag))

        self.stdout.write(self.style.SUCCESS(f"{len(enrollments)} Enrollments processed."))

        # ---------------------------------------------------
        # REALISTIC ATTENDANCE + SYSTEM RFID SCANS
        # ---------------------------------------------------
  
        days_mapping = {
            'mw': [0, 2],       # Mon, Wed
            'uth': [6, 1, 3],   # Sun, Tue, Thu
        }

        today = timezone.localdate()
        scans_to_create = []
        attendances_to_create = []

        self.stdout.write(self.style.WARNING("Simulating historical attendance records... (this may take a moment)"))

        for enrollment, tag in enrollments:
            section = enrollment.course_info
            valid_weekdays = days_mapping.get(section.days, [])

            # Check previous 10 days to find valid session matches
            for days_back in range(10):
                session_date = today - timedelta(days=days_back)
                
                # Check if this course actually runs on this specific weekday
                if session_date.weekday() not in valid_weekdays:
                    continue

                # Determine a realistic student status
                # 85% chance Present, 5% Late, 10% Absent
                attendance_roll = random.random()
                if attendance_roll < 0.85:
                    status = "PRESENT"
                elif attendance_roll < 0.90:
                    status = "LATE"
                else:
                    status = "ABSENT"

                # Combine the target schedule date with target schedule times
                class_start_dt = datetime.combine(session_date, section.start_time)
                class_end_dt = datetime.combine(session_date, section.end_time)

                if status == "PRESENT":
                    # Arrives 10 to 2 minutes BEFORE class starts
                    arrival = class_start_dt - timedelta(minutes=random.randint(2, 10))
                    # Departs 0 to 5 minutes AFTER class ends
                    departure = class_end_dt + timedelta(minutes=random.randint(0, 5))
                elif status == "LATE":
                    # Arrives 5 to 20 minutes AFTER class starts
                    arrival = class_start_dt + timedelta(minutes=random.randint(5, 20))
                    departure = class_end_dt + timedelta(minutes=random.randint(0, 5))
                else: # ABSENT
                    # No scans, but an explicit ABSENT row is tracked by the school system
                    attendance = Attendance.objects.create(
                        student=enrollment.student,
                        course_info=section,
                        session_date=session_date,
                        first_seen=timezone.make_aware(class_start_dt),
                        last_seen=timezone.make_aware(class_start_dt),
                        status="ABSENT",
                        device_id="ESP32-ROOM-01"
                    )
                    continue

                # Make times timezone aware for Django
                arrival_aware = timezone.make_aware(arrival)
                departure_aware = timezone.make_aware(departure)

                # Generate the physical system log scans
                scan_in = RfidScan.objects.create(
                    uid=tag.tag_uid,
                    user=enrollment.student,
                    tag=tag,
                    device_id="ESP32-ROOM-01",
                    source_ip=f"192.168.1.{random.randint(10, 250)}",
                    status="IN",
                    success=True,
                )
                scan_in.created_at = arrival_aware
                scan_in.save()

                scan_out = RfidScan.objects.create(
                    uid=tag.tag_uid,
                    user=enrollment.student,
                    tag=tag,
                    device_id="ESP32-ROOM-01",
                    source_ip=f"192.168.1.{random.randint(10, 250)}",
                    status="OUT",
                    success=True,
                )
                scan_out.created_at = departure_aware
                scan_out.save()

                # Generate matching finalized attendance record
                attendance = Attendance.objects.create(
                    student=enrollment.student,
                    course_info=section,
                    session_date=session_date,
                    first_seen=arrival_aware,
                    last_seen=departure_aware,
                    status=status,
                    device_id="ESP32-ROOM-01",
                )
                attendance.scans.add(scan_in, scan_out)

        # Update warnings dynamically based on the newly computed fake histories
        for student, _ in students:
            for enroll in Enrollment.objects.filter(student=student):
                absences = Attendance.objects.filter(student=student, course_info=enroll.course_info, status="ABSENT").count()
                if absences >= 3:
                    enroll.failed_due_to_attendance = True
                    enroll.attendance_warning_level = 2
                elif absences >= 1:
                    enroll.attendance_warning_level = 1
                enroll.save()

        self.stdout.write(self.style.SUCCESS("Attendance data generated with realistic tracking logs."))
        self.stdout.write(self.style.SUCCESS("FAKE DATABASE GENERATED SUCCESSFULLY!"))