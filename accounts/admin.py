from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import CustomUser
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin
from django.db import transaction

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('phone_number', 'username', 'real_name', 'show_avatar', 
                   'show_groups', 'date_joined', 'last_login', 'is_active', 'get_age')
    list_filter = ('groups', 'is_active', 'date_joined', 'last_login')
    search_fields = ('phone_number', 'username', 'real_name', 'email')
    ordering = ('-date_joined',)
    
    fieldsets = (
        ('账号信息', {'fields': ('phone_number', 'password')}),
        ('个人信息', {'fields': ('username', 'real_name', 'email', 'birthday', 'avatar')}),
        ('用户组和权限', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
            'description': '设置用户组和具体权限'
        }),
        ('重要日期', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'username', 'real_name', 'birthday', 'password1', 'password2', 'groups'),
        }),
    )
    
    def show_avatar(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width: 30px; height: 30px; border-radius: 50%;" />',
                obj.avatar.url
            )
        return "无头像"
    show_avatar.short_description = '头像'
    
    def show_groups(self, obj):
        groups = obj.groups.all()
        if groups:
            return format_html(
                '<span style="color: {};">{}</span>',
                self.get_group_color(groups[0].name),
                ', '.join([g.name for g in groups])
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
    
    def get_age(self, obj):
        if obj.birthday:
            today = timezone.now().date()
            age = today.year - obj.birthday.year
            if today.month < obj.birthday.month or (today.month == obj.birthday.month and today.day < obj.birthday.day):
                age -= 1
            return f"{age}岁"
        return "未设置"
    get_age.short_description = '年龄'
    
    readonly_fields = ('last_login', 'date_joined')
    
    actions = ['activate_users', 'deactivate_users', 'set_as_vip', 'set_as_member']
    
    def activate_users(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'成功激活 {updated} 个用户')
    activate_users.short_description = '激活选中的用户'
    
    def deactivate_users(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'成功禁用 {updated} 个用户')
    deactivate_users.short_description = '禁用选中的用户'

    def set_as_vip(self, request, queryset):
        vip_group = Group.objects.get(name='VIP')
        for user in queryset:
            user.groups.clear()
            user.groups.add(vip_group)
        self.message_user(request, f'已将选中用户设置为VIP')
    set_as_vip.short_description = '设置为VIP'

    def set_as_member(self, request, queryset):
        member_group = Group.objects.get(name='会员')
        for user in queryset:
            user.groups.clear()
            user.groups.add(member_group)
        self.message_user(request, f'已将选中用户设置为会员')
    set_as_member.short_description = '设置为会员'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(is_superuser=False)  # 非超级管理员只能看到普通用户

    def save_model(self, request, obj, form, change):
        # 如果是新创建的用户且没有组，添加到"用户"组
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
