from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from django.db import transaction
from files.models import UserStorageQuota
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _

class UserStorageQuotaInline(admin.StackedInline):
    model = UserStorageQuota
    can_delete = False
    readonly_fields = ('used_storage',)
    extra = 0
    
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if not request.user.is_superuser:
            fields = [f for f in fields if f != 'max_storage']
        return fields

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'phone_number', 'show_avatar', 'real_name', 
        'show_storage_usage', 'show_groups', 'last_login_status',
        'is_active', 'show_file_count'
    )
    list_filter = (
        'is_active', 'groups', 'date_joined', 'last_login',
        'is_staff', 'is_superuser'
    )
    search_fields = ('username', 'phone_number', 'real_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('username', 'phone_number', 'password')}),
        ('个人信息', {'fields': (
            'real_name', 'birthday', 'avatar', 'email',
            'get_age'
        )}),
        ('权限', {'fields': (
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions'
        )}),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
        ('统计信息', {'fields': (
            'show_storage_details', 'show_file_statistics',
            'show_login_history'
        )}),
    )
    
    readonly_fields = (
        'date_joined', 'last_login', 'get_age',
        'show_storage_details', 'show_file_statistics',
        'show_login_history'
    )
    
    actions = [
        'activate_users', 'deactivate_users',
        'set_as_vip', 'set_as_member', 'reset_storage_quota',
        'export_user_data', 'send_notification'
    ]
    
    inlines = [UserStorageQuotaInline]

    def show_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; '
                'border-radius: 50%; object-fit: cover;" />',
                obj.avatar.url
            )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 50%; '
            'background: #e0e0e0; display: flex; align-items: center; '
            'justify-content: center;">{}</div>',
            obj.username[0].upper()
        )
    show_avatar.short_description = '头像'

    def show_storage_usage(self, obj):
        try:
            quota = obj.storage_quota
            usage_percent = quota.get_storage_usage_percent()
            color = '#28a745' if usage_percent < 80 else '#dc3545'
            
            # 分开构建 HTML 字符串
            progress_bar = format_html(
                '<div style="width: 100px;">'
                '<div style="height: 8px; background: #f0f0f0; '
                'border-radius: 4px; overflow: hidden;">'
                '<div style="width: {}%; height: 100%; background: {};">'
                '</div></div>',
                min(usage_percent, 100),
                color
            )
            
            usage_text = format_html(
                '<small style="color: {}">{} ({}/{})</small>'
                '</div>',
                color,
                format_html('{}%', format(usage_percent, '.1f')),
                self.format_size(quota.used_storage),
                self.format_size(quota.max_storage)
            )
            
            return format_html('{}{}', progress_bar, usage_text)
        except UserStorageQuota.DoesNotExist:
            return '未设置'
    show_storage_usage.short_description = '存储使用'

    def show_file_count(self, obj):
        file_counts = obj.files.values('file_type').annotate(count=Count('id'))
        counts_html = []
        for count in file_counts:
            counts_html.append(format_html(
                '{}: {}',
                count['file_type'],
                count['count']
            ))
        return format_html('<br>'.join(counts_html)) if counts_html else '无文件'
    show_file_count.short_description = '文件统计'

    def last_login_status(self, obj):
        if not obj.last_login:
            return '从未登录'
        
        last_login = obj.last_login
        now = timezone.now()
        diff = now - last_login
        
        if diff.days == 0:
            if diff.seconds < 3600:
                return format_html(
                    '<span style="color: #28a745">在线</span>'
                )
            return '今天'
        elif diff.days < 7:
            return format_html('{}天前', diff.days)
        return last_login.strftime('%Y-%m-%d')
    last_login_status.short_description = '登录状态'

    def show_storage_details(self, obj):
        try:
            quota = obj.storage_quota
            usage_percent = quota.get_storage_usage_percent()
            
            details = [
                format_html('<div class="storage-details">'),
                format_html('<p>总空间：{}</p>', self.format_size(quota.max_storage)),
                format_html(
                    '<p>已使用：{} ({}%)</p>',
                    self.format_size(quota.used_storage),
                    format(usage_percent, '.1f')
                ),
                format_html(
                    '<p>剩余空间：{}</p>',
                    self.format_size(quota.max_storage - quota.used_storage)
                ),
                format_html('</div>')
            ]
            
            return format_html(''.join('{}' * len(details)), *details)
        except UserStorageQuota.DoesNotExist:
            return '未设置存储配额'
    show_storage_details.short_description = '存储详情'

    def show_file_statistics(self, obj):
        stats = obj.files.values('file_type').annotate(
            count=Count('id'),
            total_size=Sum('file_size')
        )
        
        if not stats:
            return '无文件'
        
        parts = [format_html('<div class="file-statistics">')]
        for stat in stats:
            parts.append(format_html(
                '<p>{}: {}个文件 ({})</p>',
                stat['file_type'],
                stat['count'],
                self.format_size(stat['total_size'] or 0)
            ))
        parts.append(format_html('</div>'))
        
        return format_html(''.join('{}' * len(parts)), *parts)
    show_file_statistics.short_description = '文件统计'

    def show_login_history(self, obj):
        # 这里需要添加登录历史模型
        return '需要实现登录历史记录'
    show_login_history.short_description = '登录历史'

    def reset_storage_quota(self, request, queryset):
        count = 0
        for user in queryset:
            try:
                quota = user.storage_quota
                quota.max_storage = settings.MAX_USER_STORAGE
                quota.save()
                count += 1
            except UserStorageQuota.DoesNotExist:
                UserStorageQuota.objects.create(
                    user=user,
                    max_storage=settings.MAX_USER_STORAGE
                )
                count += 1
        self.message_user(
            request,
            format_html('已重置 {} 个用户的存储配额', count)
        )
    reset_storage_quota.short_description = '重置存储配额'

    def export_user_data(self, request, queryset):
        # 实现用户数据导出功能
        pass
    export_user_data.short_description = '导出用户数据'

    def send_notification(self, request, queryset):
        # 实现发送通知功能
        pass
    send_notification.short_description = '发送通知'

    @staticmethod
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return format_html('{} {}', format(size, '.1f'), unit)
            size /= 1024
        return format_html('{} TB', format(size, '.1f'))

    def get_age(self, obj):
        if obj.birthday:
            today = timezone.now().date()
            age = today.year - obj.birthday.year
            if today.month < obj.birthday.month or (today.month == obj.birthday.month and today.day < obj.birthday.day):
                age -= 1
            return format_html('{}岁', age)
        return "未设置"
    get_age.short_description = '年龄'

    def show_groups(self, obj):
        groups = obj.groups.all()
        if groups:
            group_names = ', '.join(g.name for g in groups)
            return format_html(
                '<span style="color: {};">{}</span>',
                self.get_group_color(groups[0].name),
                group_names
            )
        return format_html('<span style="color: #666;">普通用户</span>')
    show_groups.short_description = '用户组'

    def get_group_color(self, group_name):
        colors = {
            '管理员': '#dc3545',  # 红色
            'VIP': '#ffc107',    # 金色
            '会员': '#28a745',    # 绿色
            '用户': '#6c757d',    # 灰色
        }
        return colors.get(group_name, '#6c757d')

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if not request.user.is_superuser:
            readonly_fields = readonly_fields + ('is_staff', 'is_superuser', 'user_permissions')
        return readonly_fields

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        super().save_model(request, obj, form, change)
        if is_new and not obj.groups.exists():
            try:
                user_group = Group.objects.get(name='用户')
                obj.groups.add(user_group)
            except Group.DoesNotExist:
                pass

    class Media:
        css = {
            'all': ('admin/css/custom_admin.css',)
        }

# 取消注册默认的 GroupAdmin
admin.site.unregister(Group)

# 重新注册带有自定义显示的 GroupAdmin
@admin.register(Group)
class CustomGroupAdmin(GroupAdmin):
    list_display = ('name', 'show_member_count')
    
    def show_member_count(self, obj):
        count = obj.user_set.count()
        return format_html(
            '<span style="color: #666;">{} 名成员</span>',
            count
        )
    show_member_count.short_description = '成员数量'
