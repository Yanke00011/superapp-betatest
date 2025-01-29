from django.contrib import admin
from .models import UserFile, UserStorageQuota

@admin.register(UserStorageQuota)
class UserStorageQuotaAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_readable_quota', 'get_used_storage_display', 'get_usage_percent')
    search_fields = ('user__username', 'user__real_name')
    
    def get_used_storage_display(self, obj):
        return f"{obj.get_used_storage()/1024/1024:.1f} MB"
    get_used_storage_display.short_description = '已使用空间'
    
    def get_usage_percent(self, obj):
        return f"{obj.get_storage_usage_percent():.1f}%"
    get_usage_percent.short_description = '使用率'

@admin.register(UserFile)
class UserFileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'user', 'file_type', 'get_file_size_display', 'uploaded_at', 'is_public')
    list_filter = ('file_type', 'is_public', 'uploaded_at')
    search_fields = ('original_name', 'user__username')
    ordering = ('-uploaded_at',)
