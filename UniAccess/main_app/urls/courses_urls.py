from django.urls import path 
from main_app import views


urlpatterns = [
    path('courses/', views.courses_list, name='courses_list'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/course_form/', views.CourseCreate.as_view(), name='course_create'),
    path('courses/<int:pk>/edit/', views.CourseEdit.as_view(), name='course_edit'),
    path('courses/<int:pk>/delete/', views.CourseDelete.as_view(), name='course_delete'),
]

