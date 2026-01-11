from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('bio', 'phone_number', 'avatar')}),
        ('Безопасность (2FA)', {'fields': ('is_2fa_enabled', 'otp_code', 'otp_created_at')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('bio', 'phone_number', 'avatar')}),
        ('Безопасность (2FA)', {'fields': ('is_2fa_enabled',)}),
    )
    
    list_display = ('username', 'email', 'phone_number', 'is_2fa_enabled', 'is_staff')
