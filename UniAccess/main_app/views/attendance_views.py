import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from django.db import transaction
from main_app.models import RFIDTag
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from main_app.forms import AdminCreateStudentForm , recent_unassigned_uids
from django.views.decorators.http import require_GET



User = get_user_model()

@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def tag_to_student(request):
    """
    JSON body:
      {
        "uid": "04A1B2C3D4",
        "username": "student1"   // OR "user_id": 123
        "force": false           // optional: true to override existing bindings
      }
    """
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
    if not (username or user_id):
        return JsonResponse({"ok": False, "error": "Provide username or user_id"}, status=400)

    # find the target user
    try:
        if user_id is not None:
            user = User.objects.get(id=user_id)
        else:
            user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"ok": False, "error": "User not found"}, status=404)

    # 1) If the user already has a tag and it's different → conflict unless force
    existing_for_user = getattr(user, "rfid_tag", None)  # via related_name='rfid_tag'
    if existing_for_user and existing_for_user.tag_uid != uid and not force:
        return JsonResponse({
            "ok": False,
            "error": "User already has a different UID",
            "current_uid": existing_for_user.tag_uid
        }, status=409)

    # 2) If this UID exists for another user → conflict unless force
    try:
        tag = RFIDTag.objects.select_related("assigned_to").get(tag_uid=uid)
        if tag.assigned_to and tag.assigned_to != user and not force:
            return JsonResponse({
                "ok": False,
                "error": "UID already assigned to another user",
                "assigned_to": tag.assigned_to.username
            }, status=409)
    except RFIDTag.DoesNotExist:
        tag = None

    # Apply assignment
    if tag is None:
        tag = RFIDTag.objects.create(tag_uid=uid, assigned_to=user)
    else:
        tag.assigned_to = user
        tag.save(update_fields=["assigned_to"])

    return JsonResponse({
        "ok": True,
        "msg": "Tag assigned",
        "uid": tag.tag_uid,
        "student": user.username,
        "student_id": user.id
    }, status=200)

try:
    from main_app.models import Attendance
    HAVE_ATT = True
except Exception:
    HAVE_ATT = False

@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def rfid_scan(request):
    """
    Body:
      {"uid":"04A1B2C3D4","device_id":"ESP32-LAB","status":"SCAN"}
    Returns:
      200 if UID is assigned to a user
      404 if UID is unknown/unassigned
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    uid = (data.get("uid") or "").strip()
    device_id = (data.get("device_id") or "").strip()
    status = (data.get("status") or "SCAN").strip().upper()

    if not uid:
        return JsonResponse({"ok": False, "error": "Missing uid"}, status=400)

    # Look up tag & user
    try:
        tag = RFIDTag.objects.select_related("assigned_to").get(tag_uid=uid)
        user = tag.assigned_to
    except RFIDTag.DoesNotExist:
        tag = None
        user = None

    known = bool(tag and user)
    note = "OK" if known else "Unknown or unassigned tag"
    success = known

    # Optionally store attendance if model exists
    scanned_at = None
    if HAVE_ATT:
        try:
            rec = Attendance.objects.create(
                tag=tag,
                uid=uid,
                user=user,
                status=status if status in ["IN", "OUT", "SCAN"] else "SCAN",
                device_id=device_id or None,
                source_ip=request.META.get("REMOTE_ADDR"),
                success=success,
                note=note,
            )
            scanned_at = rec.scanned_at.isoformat()
        except Exception:
            pass

    return JsonResponse(
        {
            "ok": True,
            "uid": uid,
            "user": (user.username if user else None),
            "known_tag": known,
            "note": note,
            "scanned_at": scanned_at,
        },
        status=200 if success else 404,
    )




@staff_member_required 
def admin_create_student(request):
    if request.method == "POST":
        form = AdminCreateStudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Student created and tag assigned (if selected).")
            return redirect(reverse("admin_create_student"))
        
    else:
        form = AdminCreateStudentForm()
    return render(request, "registration/admin_create_student.html", {"form": form})





@staff_member_required
@require_GET
def latest_unassigned_uids_api(request):
    # returns up to 25 latest unassigned UIDs
    return JsonResponse({"uids": [u for (u, _) in recent_unassigned_uids()]})