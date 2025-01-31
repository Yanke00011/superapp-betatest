from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator
from django.utils import timezone
import os
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings

class CustomUser(AbstractUser):
    def get_avatar_upload_path(self, filename):
        # 确保用户目录存在
        user_path = os.path.join('avatars', str(self.id))
        full_path = os.path.join(settings.MEDIA_ROOT, user_path)
        os.makedirs(full_path, exist_ok=True)
        return os.path.join(user_path, filename)

    phone_number = models.CharField(
        '手机号码',
        max_length=11,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^1[3-9]\d{9}$',
                message='请输入有效的手机号码（11位数字，以1开头）'
            )
        ],
        help_text='请输入11位手机号码，例如：13800138000'
    )
    birthday = models.DateField(
        '出生日期',
        null=True,
        blank=True,
        help_text='请输入生日，格式：YYYY-MM-DD'
    )
    avatar = models.ImageField(
        '头像',
        upload_to=get_avatar_upload_path,  # 使用自定义的上传路径函数
        null=True,
        blank=True,
        help_text='用户头像'
    )
    real_name = models.CharField(
        '真实姓名',
        max_length=50,
        blank=True,
        help_text='请输入您的真实姓名'
    )
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return self.username

    def get_user_directory_path(self):
        # 返回用户的专属目录路径
        return f'users/{self.username}'

    def save(self, *args, **kwargs):
        if self.pk is None:  # 新用户
            super().save(*args, **kwargs)
            # 创建用户目录
            self.create_user_directories()
        else:
            # 如果更新头像，确保目录存在
            if 'avatar' in kwargs.get('update_fields', []) or 'avatar' in getattr(self, '_changed_fields', []):
                self.create_user_directories()
            super().save(*args, **kwargs)

    def create_user_directories(self):
        # 创建用户所需的目录
        avatar_path = os.path.join(settings.MEDIA_ROOT, 'avatars', str(self.id))
        os.makedirs(avatar_path, exist_ok=True)

@receiver(post_save, sender=CustomUser)
def create_user_directory(sender, instance, created, **kwargs):
    """当新用户创建时，自动创建用户目录"""
    if created:
        instance.create_user_directories()