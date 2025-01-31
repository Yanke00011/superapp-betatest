from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.conf import settings
from files.models import UserStorageQuota
import os

class Command(BaseCommand):
    help = '初始化系统：创建用户组、目录结构和默认数据'

    def handle(self, *args, **kwargs):
        self.stdout.write('开始系统初始化...')
        
        # 1. 创建基本目录结构
        self.create_directory_structure()
        
        # 2. 创建用户组
        self.create_user_groups()
        
        # 3. 初始化存储配额
        self.initialize_storage_quotas()
        
        # 4. 创建用户目录
        self.create_user_directories()
        
        self.stdout.write(self.style.SUCCESS('系统初始化完成！'))
    
    def create_directory_structure(self):
        """创建基本目录结构"""
        self.stdout.write('创建基本目录结构...')
        
        # 创建媒体根目录
        os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
        
        # 创建用户上传根目录
        users_root = os.path.join(settings.MEDIA_ROOT, 'users')
        os.makedirs(users_root, exist_ok=True)
        
        # 创建头像目录
        avatars_root = os.path.join(settings.MEDIA_ROOT, 'avatars')
        os.makedirs(avatars_root, exist_ok=True)
        
        # 设置目录权限
        for root in [settings.MEDIA_ROOT, users_root, avatars_root]:
            os.chmod(root, 0o755)
    
    def create_user_groups(self):
        """创建用户组"""
        self.stdout.write('创建用户组...')
        
        groups = {
            '管理员': Group.objects.get_or_create(name='管理员')[0],
            'VIP': Group.objects.get_or_create(name='VIP')[0],
            '会员': Group.objects.get_or_create(name='会员')[0],
            '用户': Group.objects.get_or_create(name='用户')[0],
        }
        
        # 为现有超级用户设置管理员组
        User = get_user_model()
        for user in User.objects.filter(is_superuser=True):
            user.groups.add(groups['管理员'])
            self.stdout.write(f'已将用户 {user.username} 添加到管理员组')
        
        # 为其他用户设置默认组
        for user in User.objects.filter(is_superuser=False, groups__isnull=True):
            user.groups.add(groups['用户'])
            self.stdout.write(f'已将用户 {user.username} 添加到用户组')
    
    def initialize_storage_quotas(self):
        """初始化用户存储配额"""
        self.stdout.write('初始化存储配额...')
        
        User = get_user_model()
        for user in User.objects.all():
            quota, created = UserStorageQuota.objects.get_or_create(
                user=user,
                defaults={'max_storage': settings.MAX_USER_STORAGE}
            )
            if created:
                self.stdout.write(f'已为用户 {user.username} 创建存储配额')
    
    def create_user_directories(self):
        """为每个用户创建必要的目录"""
        self.stdout.write('创建用户目录...')
        
        User = get_user_model()
        for user in User.objects.all():
            # 用户根目录
            user_root = os.path.join(settings.MEDIA_ROOT, 'users', str(user.id))
            os.makedirs(user_root, exist_ok=True)
            os.chmod(user_root, settings.MEDIA_ROOT_PERMISSIONS)
            
            # 创建文件类型目录
            for file_type in settings.ALLOWED_FILE_TYPES.keys():
                type_dir = os.path.join(user_root, file_type)
                os.makedirs(type_dir, exist_ok=True)
                os.chmod(type_dir, settings.MEDIA_ROOT_PERMISSIONS)
            
            self.stdout.write(f'已为用户 {user.username} 创建目录结构') 