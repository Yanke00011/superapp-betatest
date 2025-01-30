from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import os

@receiver(post_save, sender=CustomUser)
def create_user_directory(sender, instance, created, **kwargs):
    """确保用户相关目录创建"""
    if created:
        # 创建用户媒体目录
        user_paths = [
            os.path.join(settings.MEDIA_ROOT, f'users/{instance.id}'),
            os.path.join(settings.MEDIA_ROOT, f'users/{instance.id}/documents'),
            os.path.join(settings.MEDIA_ROOT, f'users/{instance.id}/images'),
            os.path.join(settings.MEDIA_ROOT, f'users/{instance.id}/videos'),
        ]
        for path in user_paths:
            os.makedirs(path, exist_ok=True) 