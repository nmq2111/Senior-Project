from .pages_views import home , view_Profile , edit_profile , admin_dashboard , student_dashboard , student_attendance , teacher_dashboard

from .course_views import courses_list , CourseCreate , CourseEdit , CourseDelete , CourseInfoCreate , CourseInfoEdit ,CourseInfoDelete , courseInfo_list , courseInfo_detail , register_course , drop_course , is_registration_open

from .attendance_views import latest_unassigned_uids_api, find_current_courseinfo_for_student , maybe_update_warning_and_notify , _weekday_tokens
from .attendance_api import is_student_enrolled, tag_to_student , rfid_scan

from .admin_views import _student_year_options , users_directory , create_staff , admin_create_student, attendance_list , registration_control


from .teacher_views import teacher_attendance_list , teacher_take_attendance , TeacherAttendanceEdit , attendance_take_C , teacher_userbase
