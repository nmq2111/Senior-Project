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


def _day_code_for(ts):
    """Map local weekday to our CourseInfo.days choices: 'uth', 'mw', 'fs'."""
    wd = timezone.localtime(ts).weekday()  # 0=Mon..6=Sun
    if wd in (0, 2):          # Mon, Wed
        return "mw"
    elif wd in (1, 3, 6):     # Tue, Thu, Sun
        return "uth"
    else:                     # Fri, Sat
        return "fs"
    

def find_current_courseinfo_for_student(student, ts=None):
    if not HAVE_ATT or not student:
        return None

    ts = ts or timezone.now()
    local_dt = timezone.localtime(ts)
    t = local_dt.time()
    day_code = _day_code_for(ts)

    qs = CourseInfo.objects.all()

    # Status
    try:
        qs = qs.filter(status__in=["Yes", "Available"])
    except Exception:
        pass

    # Day + time
    qs = qs.filter(days=day_code, start_time__lte=t, end_time__gte=t)

    # 🔒 Enrollment restriction
    qs = qs.filter(enrollments__student=student).distinct()

    # If multiple match (rare), pick the earliest start today
    return qs.order_by("start_time").first()


@staff_member_required
@require_GET
def latest_unassigned_uids_api(request):
    return JsonResponse({"uids": [u for (u, _) in recent_unassigned_uids()]})



