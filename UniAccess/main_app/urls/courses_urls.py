from django.urls import path 
from main_app import views


urlpatterns = [
    path('courses/', views.courses_list, name='courses_list'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/course_form/', views.CourseCreate.as_view(), name='course_create'),
    path('courses/<int:pk>/edit/', views.CourseEdit.as_view(), name='course_edit'),
    path('courses/<int:pk>/delete/', views.CourseDelete.as_view(), name='course_delete'),
    path('courses/coursesInfo/', views.courseInfo_list, name='courseInfo_list'),
    path('courses/coursesInfo/<int:pk>/', views.courseInfo_detail, name='courseInfo_detail'),
    path('courses/coursesInfo/courseInfo_form/', views.CourseInfoCreate.as_view(), name='courseInfo_create'),
    path('courses/coursesInfo/<int:pk>/edit/', views.CourseInfoEdit.as_view(), name='courseInfo_edit'),
    path('courses/coursesInfo/<int:pk>/delete/', views.CourseInfoDelete.as_view(), name='courseInfo_delete'),
]

