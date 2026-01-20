from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, EmailVerification


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = [
        'bio', 'avatar',
        'show_email', 'show_real_name',
        'total_uploads', 'total_downloads'
    ]
    readonly_fields = ['total_uploads', 'total_downloads']


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = BaseUserAdmin.list_display + ('get_total_uploads', 'get_total_downloads', 'date_joined')
    
    def get_total_uploads(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.total_uploads
        return 0
    get_total_uploads.short_description = 'Total Uploads'
    
    def get_total_downloads(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.total_downloads
        return 0
    get_total_downloads.short_description = 'Total Downloads'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'get_display_name',
        'total_uploads', 'total_downloads', 'created_at'
    ]
    list_filter = ['show_email', 'show_real_name', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'bio']
    readonly_fields = ['created_at', 'updated_at', 'total_uploads', 'total_downloads']
    raw_id_fields = ['user']
    
    fieldsets = (
        ('User Info', {
            'fields': ('user', 'bio', 'avatar')
        }),
        ('Privacy Settings', {
            'fields': ('show_email', 'show_real_name'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('total_uploads', 'total_downloads'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_display_name(self, obj):
        return obj.display_name
    get_display_name.short_description = 'Display Name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'verified', 'created_at', 'verified_at', 'is_expired_display']
    list_filter = ['verified', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['token', 'created_at', 'verified_at']
    ordering = ['-created_at']
    
    def email(self, obj):
        return obj.user.email
    email.short_description = 'Email'
    
    def is_expired_display(self, obj):
        if obj.verified:
            return 'N/A (Verified)'
        return 'Yes' if obj.is_expired() else 'No'
    is_expired_display.short_description = 'Expired'
