import json
from datetime import datetime

from dataclasses import dataclass
from typing import Tuple

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from ..forms import recent_unassigned_uids
from main_app.models import Attendance, Enrollment, CourseInfo

User = get_user_model()

SEMESTER_WEEKS = 16
LATE_PER_ABSENCE = 4
WARNING_THRESHOLDS = (0.25, 0.50, 0.75)
HAVE_ATT = True

# === Helpers ===
def _weekday_tokens(ts):
    idx = timezone.localtime(ts).weekday()
    table = {
        0: ("MO", "MON", "MONDAY"),
        1: ("TU", "TUE", "TUESDAY"),
        2: ("WE", "WED", "WEDNESDAY"),
        3: ("TH", "THU", "THURSDAY"),
        4: ("FR", "FRI", "FRIDAY"),
        5: ("SA", "SAT", "SATURDAY"),
        6: ("SU", "SUN", "SUNDAY"),
    }
    return table[idx]

def _day_code_for(ts):
    wd = timezone.localtime(ts).weekday()
    if wd in (0, 2):
        return "mw"
    elif wd in (1, 3, 6):
        return "uth"
    else:
        return "fs"

def find_current_courseinfo_for_student(student, ts=None):
    if not HAVE_ATT or not student:
        return None
    ts = ts or timezone.now()
    local_dt = timezone.localtime(ts)
    t = local_dt.time()
    day_code = _day_code_for(ts)
    qs = CourseInfo.objects.all()
    try:
        qs = qs.filter(status__in=["Yes", "Available"])
    except Exception:
        pass
    qs = qs.filter(days=day_code, start_time__lte=t, end_time__gte=t)
    qs = qs.filter(enrollments__student=student).distinct()
    return qs.order_by("start_time").first()

def _weekly_meetings(days_code: str) -> int:
    d = (days_code or "").lower()
    if d == "uth":
        return 3
    if d in ("mw", "fs"):
        return 2
    return 2

def planned_sessions(ci: CourseInfo) -> int:
    return _weekly_meetings(ci.days) * SEMESTER_WEEKS

@dataclass
class PolicyCalc:
    present: int
    late: int
    absent: int
    late_as_absence: int
    absence_equiv: int
    planned: int
    pct_absence: float
    level: int

def calculate_policy(student_id: int, ci: CourseInfo) -> PolicyCalc:
    qs = (
        Attendance.objects
        .filter(student_id=student_id, course_info=ci)
        .values("status")
        .annotate(c=Count("id"))
    )
    counts = {row["status"]: row["c"] for row in qs}
    present = counts.get("PRESENT", 0)
    late = counts.get("LATE", 0)
    absent = counts.get("ABSENT", 0)
    late_as_absence = late // LATE_PER_ABSENCE
    absence_equiv = absent + late_as_absence
    planned = planned_sessions(ci) or 1
    pct_absence = absence_equiv / planned
    if pct_absence >= WARNING_THRESHOLDS[2]:
        level = 3
    elif pct_absence >= WARNING_THRESHOLDS[1]:
        level = 2
    elif pct_absence >= WARNING_THRESHOLDS[0]:
        level = 1
    else:
        level = 0
    return PolicyCalc(
        present=present,
        late=late,
        absent=absent,
        late_as_absence=late_as_absence,
        absence_equiv=absence_equiv,
        planned=planned,
        pct_absence=pct_absence,
        level=level,
    )

def _email_subject(ci: CourseInfo, level: int) -> str:
    tag = {1: "Warning 1/3", 2: "Warning 2/3", 3: "Final Warning (3/3)"}[level]
    return f"[Attendance] {ci.course.code} – {tag}"

def _email_body(student_name: str, ci: CourseInfo, calc: PolicyCalc) -> str:
    pct = round(calc.pct_absence * 100, 1)
    lines = [
        f"Dear {student_name},",
        "",
        f"This is an attendance notice for {ci.course.code} – {ci.course.name} (Section {getattr(ci, 'section', '—')}).",
        f"Semester: {ci.year} / {ci.get_semester_display()}",
        "",
        f"• Present: {calc.present}",
        f"• Late: {calc.late} (every {LATE_PER_ABSENCE} late = 1 absence ⇒ +{calc.late_as_absence})",
        f"• Absent-equivalent total: {calc.absence_equiv} out of ~{calc.planned} planned sessions ({pct}%)",
        "",
        "Policy:",
        f"• Warnings at 25%, 50%, 75%. 4 late = 1 absence.",
        "• At 3 warnings (≥75%), you fail the course due to attendance.",
        "",
        "Please adjust your attendance accordingly.",
        "",
        "Regards,",
        "Registrar",
    ]
    return "\n".join(lines)

def maybe_update_warning_and_notify(student, ci: CourseInfo) -> Tuple[PolicyCalc, bool]:
    calc = calculate_policy(student.id, ci)
    try:
        enr = Enrollment.objects.get(student=student, course_info=ci)
    except Enrollment.DoesNotExist:
        return calc, False
    notified = False
    if calc.level > enr.attendance_warning_level:
        enr.attendance_warning_level = calc.level
        if calc.level >= 3:
            enr.failed_due_to_attendance = True
        enr.save(update_fields=["attendance_warning_level", "failed_due_to_attendance"])
        to_email = (student.email or "").strip()
        if to_email:
            try:
                send_mail(
                    subject=_email_subject(ci, calc.level),
                    message=_email_body(student.get_full_name() or student.username, ci, calc),
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[to_email],
                    fail_silently=True,
                )
                notified = True
            except Exception:
                pass
    return calc, notified

# === Views ===
@staff_member_required
@require_GET
def latest_unassigned_uids_api(request):
    return JsonResponse({"uids": [u for (u, _) in recent_unassigned_uids()]})

@login_required
@require_POST
@transaction.atomic
def student_checkout_api(request):
    if getattr(request.user, "role", None) != "student":
        return HttpResponseForbidden("Students only.")
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)
    ci_id = payload.get("course_info_id")
    date_str = (payload.get("date") or "").strip()
    if not ci_id:
        return JsonResponse({"ok": False, "error": "Missing course_info_id"}, status=400)
    ci = get_object_or_404(CourseInfo.objects.select_related("course"), id=ci_id)
    try:
        session_date = timezone.localdate() if not date_str else datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        session_date = timezone.localdate()
    try:
        att = Attendance.objects.get(student=request.user, course_info=ci, session_date=session_date)
    except Attendance.DoesNotExist:
        return JsonResponse({"ok": False, "error": "No attendance record for this class/date."}, status=404)
    now = timezone.now()
    start_dt = timezone.make_aware(datetime.combine(session_date, ci.start_time))
    end_dt = timezone.make_aware(datetime.combine(session_date, ci.end_time))
    if now < start_dt:
        return JsonResponse({"ok": False, "error": "Not within class time window."}, status=400)
    checkout_time = min(now, end_dt)
    current_last = att.last_seen or att.first_seen or start_dt
    if checkout_time > current_last:
        att.last_seen = checkout_time
        att.device_id = att.device_id or "STUDENT-CHECKOUT"
        att.save(update_fields=["last_seen", "device_id"])
        return JsonResponse(
            {
                "ok": True,
                "attendance_id": att.id,
                "session_date": session_date.isoformat(),
                "updated_last_seen": timezone.localtime(checkout_time).strftime("%Y-%m-%d %H:%M:%S"),
            },
            status=200,
        )
    return JsonResponse(
        {
            "ok": True,
            "attendance_id": att.id,
            "session_date": session_date.isoformat(),
            "updated_last_seen": timezone.localtime(current_last).strftime("%Y-%m-%d %H:%M:%S"),
            "note": "No change",
        },
        status=200,
    )
