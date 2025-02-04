from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
import os
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings

class CustomUser(AbstractUser):
    phone_number = models.CharField(
        '手机号码',
        max_length=11,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^1[3-9]\d{9}$',
                message='请输入有效的手机号码（11位数字，以1开头）'
            )
        ]
    )
    birthday = models.DateField('出生日期', null=True, blank=True)
    avatar = models.ImageField('头像', upload_to='avatars/', null=True, blank=True)
    real_name = models.CharField('真实姓名', max_length=50, blank=True)
    registration_ip = models.GenericIPAddressField(
        '注册IP',
        null=True,
        blank=True,
        help_text='用户注册时的IP地址'
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.username or self.phone_number

    def save(self, *args, **kwargs):
        creating = self._state.adding
        super().save(*args, **kwargs)
        if creating:
            # 创建用户时自动创建存储配额
            from files.models import UserStorageQuota
            UserStorageQuota.objects.create(
                user=self,
                max_storage=settings.MAX_USER_STORAGE
            )

    def get_avatar_upload_path(self, filename):
        # 确保用户目录存在
        user_path = os.path.join('avatars', str(self.id))
        full_path = os.path.join(settings.MEDIA_ROOT, user_path)
        os.makedirs(full_path, exist_ok=True)
        return os.path.join(user_path, filename)

    def get_user_directory_path(self):
        # 返回用户的专属目录路径
        return f'users/{self.username}'

    def create_user_directories(self):
        # 创建用户所需的目录
        avatar_path = os.path.join(settings.MEDIA_ROOT, 'avatars', str(self.id))
        os.makedirs(avatar_path, exist_ok=True)

@receiver(post_save, sender=CustomUser)
def create_user_directory(sender, instance, created, **kwargs):
    """当新用户创建时，自动创建用户目录"""
    if created:
        instance.create_user_directories()