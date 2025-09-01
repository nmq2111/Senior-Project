import json
from datetime import timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db import transaction
from main_app.models import RFIDTag, Attendance
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse

# Optional: avoid duplicate spam within N seconds (e.g., same UID bouncing on reader)
DEDUP_WINDOW_SEC = 8

@csrf_exempt  # Devices can't do CSRF; secure via network/Tokens later if needed
@require_http_methods(["POST"])
@transaction.atomic
def rfid_scan(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    uid = (data.get("uid") or "").strip()
    device_id = (data.get("device_id") or "").strip()
    status = (data.get("status") or "SCAN").strip().upper()  # optionally IN/OUT

    if not uid:
        return JsonResponse({"ok": False, "error": "Missing uid"}, status=400)

    # De-dup (same UID too soon)
    cutoff = timezone.now() - timedelta(seconds=DEDUP_WINDOW_SEC)
    if Attendance.objects.filter(uid=uid, scanned_at__gte=cutoff).exists():
        return JsonResponse({"ok": True, "dedup": True, "msg": "Ignored duplicate scan"}, status=200)

    # Try to find a registered tag
    user = None
    tag = None
    success = True
    note = None

    try:
        tag = RFIDTag.objects.select_related('assigned_to').get(tag_uid=uid)
        user = tag.assigned_to
        if user is None:
            success = False
            note = "Tag is registered but not assigned to a user."
    except RFIDTag.DoesNotExist:
        success = False
        note = "Unknown UID"

    rec = Attendance.objects.create(
        tag=tag,
        uid=uid,
        user=user,
        status=status if status in ["IN", "OUT", "SCAN"] else "SCAN",
        device_id=device_id or None,
        source_ip=request.META.get("REMOTE_ADDR"),
        success=success,
        note=note
    )

    return JsonResponse({
        "ok": True,
        "record_id": rec.id,
        "uid": uid,
        "user": (user.username if user else None),
        "known_tag": bool(tag),
        "success": success,
        "note": note,
        "scanned_at": rec.scanned_at.isoformat()
    }, status=200 if success else 404)





def attendance_list(request):
    qs = Attendance.objects.select_related('user').order_by('-scanned_at')[:200]
    return render(request, 'attendance/attendance_list.html', {'records': qs})

def unassigned_list(request):
    qs = Attendance.objects.filter(user__isnull=True).order_by('-scanned_at')[:200]
    return render(request, 'attendance/unassigned_list.html', {'records': qs})

def assign_uid_to_user(request, record_id):
    User = get_user_model()
    rec = get_object_or_404(Attendance, id=record_id)
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        user = get_object_or_404(User, username=username)

        # ensure tag exists (create if first time)
        tag, _ = RFIDTag.objects.get_or_create(tag_uid=rec.uid)
        tag.assigned_to = user
        tag.save()

        # backfill this record’s user
        rec.user = user
        rec.tag = tag
        rec.success = True
        rec.note = None
        rec.save(update_fields=["user", "tag", "success", "note"])

        messages.success(request, f"Assigned UID {rec.uid} to {user.username}")
        return redirect(reverse('unassigned_list'))
    return render(request, 'attendance/assign_uid.html', {'rec': rec})
