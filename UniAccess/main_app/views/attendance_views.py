import json
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from ..models import RfidScan, RFIDTag ,Profile 
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.shortcuts import render, redirect
from django.conf import settings
from ..forms import CreateRFIDForm
from django.db.models import Max


API_TOKEN = "dev-123" 

@csrf_exempt
def ingest_scan(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")

    if request.headers.get("X-API-KEY") != API_TOKEN:
        return HttpResponseForbidden("Invalid token")

    try:
        data = json.loads(request.body.decode("utf-8"))
        uid = (data.get("uid") or "").strip().upper()
        device_id = (data.get("device_id") or None)
        extra = data.get("extra")
    except Exception:
        return HttpResponseBadRequest("Bad JSON")

    if not uid:
        return HttpResponseBadRequest("Missing uid")

    # 1) Log the scan
    scan = RfidScan.objects.create(uid=uid, device_id=device_id, extra=extra)

    # 2) Ensure a catalog row exists for this UID (unassigned until admin links)
    RFIDTag.objects.get_or_create(tag_uid=uid)

    return JsonResponse({"ok": True, "scan_id": scan.id})

def is_admin(u):
    return u.is_staff or getattr(u, 'role', '') == 'admin'

@login_required
@user_passes_test(is_admin)
@transaction.atomic
def admin_signup_assign_rfid(request):
    assigned_uids = RFIDTag.objects.filter(assigned_to__isnull=False).values_list('tag_uid', flat=True)

    # recent *unassigned* UIDs, one row per UID with latest timestamp
    recent_scans = (
        RfidScan.objects
        .exclude(uid__in=assigned_uids)
        .values('uid')
        .annotate(last_seen=Max('created_at'))
        .order_by('-last_seen')[:10]
    )

    suggested_uid = recent_scans[0]['uid'] if recent_scans else None

    if request.method == 'POST':
        form = CreateRFIDForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'student'
            user.college = form.cleaned_data['college']
            user.save()
            Profile.objects.create(user=user)

            uid = form.cleaned_data['tag_uid'].strip().upper()
            tag, _ = RFIDTag.objects.get_or_create(tag_uid=uid)
            tag.assigned_to = user
            tag.save()

            messages.success(request, f"Created {user.username} and linked RFID {uid}.")
            return redirect('admin_signup_assign_rfid')
    else:
        init = {'tag_uid': suggested_uid} if suggested_uid else {}
        form = CreateRFIDForm(initial=init)

    return render(request, 'registration/signup_admin_assign.html', {
        'form': form,
        'recent_scans': recent_scans,
    })



@login_required
@user_passes_test(is_admin)
def recent_unassigned_scans_api(request):
    assigned = RFIDTag.objects.filter(assigned_to__isnull=False).values_list('tag_uid', flat=True)
    rows = list(
        RfidScan.objects
        .exclude(uid__in=assigned)
        .values('uid')
        .annotate(last_seen=Max('created_at'))
        .order_by('-last_seen')[:10]
    )
    return JsonResponse({"items": rows})