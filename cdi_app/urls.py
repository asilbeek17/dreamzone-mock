from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # User Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('book-test/', views.book_test_view, name='book_test'),
    path('booking/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('booking/<int:booking_id>/feedback/', views.submit_feedback_view, name='submit_feedback'),
    
    # AJAX
    path('api/available-times/', views.get_available_times, name='get_available_times'),
    
    # Admin
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/bookings/', views.admin_bookings_view, name='admin_bookings'),
    path('admin/booking/<int:booking_id>/', views.admin_booking_detail_view, name='admin_booking_detail'),
    path('admin/booking/<int:booking_id>/upload-result/', views.admin_upload_result_view, name='admin_upload_result'),
    path('admin/feedbacks/', views.admin_feedbacks_view, name='admin_feedbacks'),
    path('admin/users/', views.admin_users_view, name='admin_users'),
    path('admin/schedule/', views.admin_schedule_view, name='admin_schedule'),
    path('admin/answers/', views.admin_answers_view, name='admin_answers'),
]
