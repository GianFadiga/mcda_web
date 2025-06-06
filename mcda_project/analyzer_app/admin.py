# mcda_project\analyzer_app\admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserLog, AnalysisLog, Analysis
from django.utils.translation import gettext_lazy as _
import json
from django.utils.html import format_html

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username',)}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

    search_fields = ('email', 'username')

@admin.register(UserLog)
class UserLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'action', 'timestamp', 'pretty_new_data')
    list_filter = ('action', 'timestamp', 'user')
    search_fields = ('user__username', 'action', 'old_data', 'new_data')
    readonly_fields = ('user', 'action', 'old_data', 'new_data', 'timestamp')

    def pretty_new_data(self, obj):
        if obj.new_data:
            try:
                data = json.loads(obj.new_data)
                pretty = json.dumps(data, indent=2)
                return format_html('<pre>{}</pre>', pretty)
            except Exception:
                return obj.new_data
        return '-'
    pretty_new_data.short_description = 'New Data'

@admin.register(AnalysisLog)
class AnalysisLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'analysis', 'action', 'timestamp')
    list_filter = ('action', 'timestamp', 'analysis')
    search_fields = ('analysis__name', 'action', 'old_data', 'new_data')
    readonly_fields = ('analysis', 'action', 'old_data', 'new_data', 'timestamp')

@admin.register(Analysis)
class AnalysisAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'creation_date')
    search_fields = ('name', 'user__email')
    actions = ['delete_selected']

    def delete_model(self, request, obj):
        obj.delete()

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()