from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from ..forms import  recent_unassigned_uids


User = get_user_model()

try:
    from ..models import Attendance, CourseInfo, Enrollment
    HAVE_ATT = True
except Exception:
    HAVE_ATT = False



def _weekday_tokens(ts):
    """Return tokens that might appear in CourseInfo.days for today's weekday."""
    idx = timezone.localtime(ts).weekday()  # 0=Mon..6=Sun
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



def find_current_courseinfo_for_student(student, ts=None):
    """
    Return an active CourseInfo at ts.
    NOTE: Enrollment filter is DISABLED to ensure we match the class window first.
    """
    if not HAVE_ATT:
        return None

    ts = ts or timezone.now()
    local_dt = timezone.localtime(ts)
    t = local_dt.time()

    idx = local_dt.weekday() 
    tokens_map = {
        0: ("MO", "MON", "MONDAY", "MW"),
        1: ("TU", "TUE", "TUESDAY", "uth" ),
        2: ("WE", "WED", "WEDNESDAY" , "MW"),
        3: ("TH", "THU", "THURSDAY" , "uth"),
        4: ("FR", "FRI", "FRIDAY" , "fs"),
        5: ("SA", "SAT", "SATURDAY" , "fs"),
        6: ("SU", "SUN", "SUNDAY" , "uth"),
    }
    tokens = tokens_map[idx]

    qs = CourseInfo.objects.all()

    try:
        qs = qs.filter(status__in=["Yes", "Available"])
    except Exception:
        pass

    try:
        day_qs = qs.none()
        for tok in tokens:
            day_qs = day_qs | qs.filter(days__icontains=tok)
        qs = day_qs.distinct()
    except Exception:
        pass

    try:
        qs = qs.filter(start_time__lte=t, end_time__gte=t)
    except Exception:
        pass

    return qs.first()


@staff_member_required
@require_GET
def latest_unassigned_uids_api(request):
    return JsonResponse({"uids": [u for (u, _) in recent_unassigned_uids()]})
