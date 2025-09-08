from .pages_views import home , signup_view , view_Profile , edit_profile

from .course_views import courses_list , course_detail , CourseCreate , CourseEdit , CourseDelete , CourseInfoCreate , CourseInfoEdit ,CourseInfoDelete , courseInfo_list , courseInfo_detail , register_course , drop_course

from .attendance_views import admin_create_student , latest_unassigned_uids_api, find_current_courseinfo_for_student 
from .attendance_api import is_student_enrolled, tag_to_student , rfid_scan