from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, Booking, Result, Feedback


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    list_display = ['username', 'full_name', 'email', 'phone_number', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'full_name', 'email', 'phone_number']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Additional Info'), {'fields': ('full_name', 'phone_number')}),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('Additional Info'), {'fields': ('full_name', 'phone_number', 'email')}),
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Booking Admin"""
    list_display = ['user', 'test_date', 'test_time', 'status', 'created_at']
    list_filter = ['status', 'test_date', 'created_at']
    search_fields = ['user__username', 'user__full_name', 'user__phone_number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Booking Information'), {
            'fields': ('user', 'test_date', 'test_time', 'payment_screenshot')
        }),
        (_('Status'), {
            'fields': ('status', 'admin_notes')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    """Result Admin"""
    list_display = ['booking', 'listening', 'reading', 'writing', 'speaking', 'overall', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['booking__user__username', 'booking__user__full_name']
    readonly_fields = ['overall', 'uploaded_at']
    
    fieldsets = (
        (_('Test Scores'), {
            'fields': ('booking', 'listening', 'reading', 'writing', 'speaking', 'overall')
        }),
        (_('Upload Info'), {
            'fields': ('uploaded_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('booking', 'booking__user')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """Feedback Admin"""
    list_display = ['user', 'booking', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['user__username', 'user__full_name', 'comment']
    readonly_fields = ['created_at']
    
    fieldsets = (
        (_('Feedback Information'), {
            'fields': ('user', 'booking', 'rating', 'comment')
        }),
        (_('Timestamp'), {
            'fields': ('created_at',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'booking')
