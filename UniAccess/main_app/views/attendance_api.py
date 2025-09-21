import json
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from main_app.views.attendance_views import (
    find_current_courseinfo_for_student,
    _weekday_tokens,
    maybe_update_warning_and_notify,
)
from ..models import RFIDTag, RfidScan

try:
    from ..models import Attendance, CourseInfo, Enrollment
    HAVE_ATT = True
except Exception:
    HAVE_ATT = False

User = get_user_model()

COOLDOWN_SEC = 3
LATE_THRESHOLD_MIN = 10

# === Helpers ===
def is_student_enrolled(student, course_info) -> bool:
    if not (student and course_info):
        return False
    return Enrollment.objects.filter(student=student, course_info=course_info).exists()


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def tag_to_student(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    uid = (data.get("uid") or "").strip()
    username = (data.get("username") or "").strip()
    user_id = data.get("user_id")
    force = bool(data.get("force", False))

    if not uid:
        return JsonResponse({"ok": False, "error": "Missing uid"}, status=400)
    if not (username or user_id is not None):
        return JsonResponse({"ok": False, "error": "Provide username or user_id"}, status=400)

    try:
        target_user = (
            User.objects.get(id=user_id) if user_id is not None else User.objects.get(username=username)
        )
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "User not found"}, status=404)

    existing_for_user = getattr(target_user, "rfid_tag", None)
    if existing_for_user and existing_for_user.tag_uid != uid and not force:
        return JsonResponse(
            {"ok": False, "error": "User already has a different UID", "current_uid": existing_for_user.tag_uid},
            status=409,
        )

    try:
        tag = RFIDTag.objects.select_related("assigned_to").get(tag_uid=uid)
        if tag.assigned_to and tag.assigned_to != target_user and not force:
            return JsonResponse(
                {"ok": False, "error": "UID already assigned to another user", "assigned_to": tag.assigned_to.username},
                status=409,
            )
    except RFIDTag.DoesNotExist:
        tag = None

    if tag is None:
        tag = RFIDTag.objects.create(tag_uid=uid, assigned_to=target_user)
    else:
        tag.assigned_to = target_user
        tag.save(update_fields=["assigned_to"])

    return JsonResponse(
        {"ok": True, "msg": "Tag assigned", "uid": tag.tag_uid, "student": target_user.username, "student_id": target_user.id},
        status=200,
    )


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def rfid_scan(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    uid = (data.get("uid") or "").strip()
    device_id = (data.get("device_id") or "").strip()
    status = (data.get("status") or "SCAN").strip().upper()
    if status not in ("IN", "OUT", "SCAN"):
        status = "SCAN"

    if not uid:
        return JsonResponse({"ok": False, "error": "Missing uid"}, status=400)

    ts = timezone.now()
    source_ip = request.META.get("REMOTE_ADDR")

    user = None
    try:
        tag = RFIDTag.objects.select_related("assigned_to").get(tag_uid=uid)
        user = tag.assigned_to
    except RFIDTag.DoesNotExist:
        tag = None

    known = bool(user)

    try:
        RfidScan.objects.create(
            uid=uid,
            user=user if known else None,
            tag=tag if tag else None,
            device_id=device_id or None,
            extra={
                "ts": ts.isoformat(),
                "status": status,
                "source_ip": source_ip,
                "known": known,
                "note": ("OK" if known else "Unknown/Unassigned"),
            },
        )
    except Exception as e:
        return JsonResponse({"ok": False, "error": f"RfidScan write failed: {str(e)}"}, status=500)

    if not known:
        return JsonResponse(
            {
                "ok": True,
                "known_tag": False,
                "uid": uid,
                "user": None,
                "note": "Unknown or unassigned tag",
                "scanned_at": ts.isoformat(),
                "lcd_line1": "Unknown tag",
                "lcd_line2": "Assign in portal",
                "debug": {"now_local": timezone.localtime(ts).strftime("%Y-%m-%d %H:%M:%S")},
            },
            status=404,
        )

    if not HAVE_ATT:
        display_name = (user.get_full_name() or user.username).strip()
        return JsonResponse(
            {
                "ok": True,
                "known_tag": True,
                "uid": uid,
                "user": user.username,
                "display_name": display_name,
                "note": "Attendance module not installed; raw scan logged.",
                "scanned_at": ts.isoformat(),
                "debug": {"now_local": timezone.localtime(ts).strftime("%Y-%m-%d %H:%M:%S")},
            },
            status=200,
        )

    ci = find_current_courseinfo_for_student(user, ts=ts)
    display_name = (user.get_full_name() or user.username).strip()

    if not ci:
        tokens = _weekday_tokens(ts)
        match_count = CourseInfo.objects.filter(
            status__in=["Yes", "Available"],
            days__icontains=tokens[2],
            start_time__lte=timezone.localtime(ts).time(),
            end_time__gte=timezone.localtime(ts).time(),
        ).count()
        return JsonResponse(
            {
                "ok": True,
                "known_tag": True,
                "uid": uid,
                "user": user.username,
                "display_name": display_name,
                "note": "No active class now",
                "scanned_at": ts.isoformat(),
                "lcd_line1": f"Hi {display_name}",
                "lcd_line2": "No class now",
                "debug": {
                    "now_local": timezone.localtime(ts).strftime("%Y-%m-%d %H:%M:%S"),
                    "weekday_tokens": list(tokens),
                    "matches_without_enrollment": match_count,
                },
            },
            status=200,
        )

    if not is_student_enrolled(user, ci):
        return JsonResponse(
            {
                "ok": True,
                "known_tag": True,
                "uid": uid,
                "user": user.username,
                "display_name": display_name,
                "note": "Not enrolled in this class",
                "scanned_at": ts.isoformat(),
                "lcd_line1": f"Hi {display_name}",
                "lcd_line2": "Not enrolled",
                "debug": {
                    "now_local": timezone.localtime(ts).strftime("%Y-%m-%d %H:%M:%S"),
                    "course_info_id": getattr(ci, "id", None),
                },
            },
            status=200,
        )

    session_date = timezone.localdate(ts)
    try:
        att, created = Attendance.objects.get_or_create(
            student=user,
            course_info=ci,
            session_date=session_date,
            defaults={"first_seen": ts, "last_seen": ts, "status": "PRESENT"},
        )

        if not created:
            recent_cutoff = (att.last_seen or att.first_seen or ts - timedelta(hours=1)) + timedelta(seconds=COOLDOWN_SEC)
            if ts >= recent_cutoff:
                att.last_seen = ts

        if created and getattr(ci, "start_time", None):
            start_dt = timezone.make_aware(datetime.combine(session_date, ci.start_time))
            if ts > start_dt + timedelta(minutes=LATE_THRESHOLD_MIN):
                att.status = "LATE"

        att.device_id = device_id or att.device_id
        att.save()

        calc, notified = maybe_update_warning_and_notify(user, ci)

    except Exception as e:
        return JsonResponse(
            {
                "ok": True,
                "known_tag": True,
                "uid": uid,
                "user": user.username,
                "display_name": display_name,
                "note": f"Scan logged; attendance error: {str(e)}",
                "scanned_at": ts.isoformat(),
                "debug": {
                    "now_local": timezone.localtime(ts).strftime("%Y-%m-%d %H:%M:%S"),
                    "course_info_id": getattr(ci, "id", None),
                    "start_time": str(getattr(ci, "start_time", "")),
                    "end_time": str(getattr(ci, "end_time", "")),
                },
            },
            status=200,
        )

    return JsonResponse(
        {
            "ok": True,
            "known_tag": True,
            "uid": uid,
            "user": user.username,
            "display_name": display_name,
            "course_info": str(ci),
            "session_date": str(session_date),
            "attendance_id": att.id,
            "created": created,
            "status": att.status,
            "note": (
                "Marked present"
                if created and att.status == "PRESENT"
                else ("Marked late" if created and att.status == "LATE" else "Updated")
            ),
            "lcd_line1": f"Welcome {display_name}",
            "lcd_line2": f"{att.status.title()}",
            "policy": {
                "present": calc.present,
                "late": calc.late,
                "absent": calc.absent,
                "late_as_absence": calc.late_as_absence,
                "absence_equiv": calc.absence_equiv,
                "planned": calc.planned,
                "pct_absence": round(calc.pct_absence * 100, 1),
                "level": calc.level,
                "notified": notified,
            },
            "debug": {
                "now_local": timezone.localtime(ts).strftime("%Y-%m-%d %H:%M:%S"),
                "course_info_id": getattr(ci, "id", None),
                "start_time": str(getattr(ci, "start_time", "")),
                "end_time": str(getattr(ci, "end_time", "")),
            },
        },
        status=200,
    )
