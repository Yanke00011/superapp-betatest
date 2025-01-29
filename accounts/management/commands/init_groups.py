from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from accounts.models import CustomUser

class Command(BaseCommand):
    help = '初始化用户组并设置现有用户的组'

    def handle(self, *args, **kwargs):
        # 创建用户组
        groups = {
            '管理员': Group.objects.get_or_create(name='管理员')[0],
            'VIP': Group.objects.get_or_create(name='VIP')[0],
            '会员': Group.objects.get_or_create(name='会员')[0],
            '用户': Group.objects.get_or_create(name='用户')[0],
        }
        
        # 设置超级用户为管理员组
        for user in CustomUser.objects.filter(is_superuser=True):
            user.groups.add(groups['管理员'])
            self.stdout.write(f'已将用户 {user.username} 添加到管理员组')
        
        # 将其他用户添加到"用户"组
        for user in CustomUser.objects.filter(is_superuser=False, groups__isnull=True):
            user.groups.add(groups['用户'])
            self.stdout.write(f'已将用户 {user.username} 添加到用户组')
        
        self.stdout.write(self.style.SUCCESS('成功初始化用户组')) 