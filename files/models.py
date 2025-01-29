from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import os

class UserStorageQuota(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='storage_quota'
    )
    max_storage = models.BigIntegerField(default=settings.MAX_USER_STORAGE)
    used_storage = models.BigIntegerField(default=0)
    
    def get_used_storage(self):
        return self.used_storage
    
    def get_readable_quota(self):
        """返回人类可读的配额大小"""
        def format_size(size):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} PB"
        
        return format_size(self.max_storage)
    
    def get_storage_usage_percent(self):
        """返回存储使用百分比"""
        if self.max_storage == 0:
            return 100
        return (self.used_storage / self.max_storage) * 100
    
    def has_sufficient_space(self, file_size):
        """检查是否有足够的存储空间"""
        return (self.used_storage + file_size) <= self.max_storage
    
    def update_used_storage(self, file_size_change):
        """更新已使用的存储空间"""
        self.used_storage = max(0, self.used_storage + file_size_change)
        self.save()

class UserFile(models.Model):
    FILE_TYPES = (
        ('image', '图片'),
        ('document', '文档'),
        ('video', '视频'),
        ('other', '其他')
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='users/%Y/%m/%d/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    original_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()  # 以字节为单位
    uploaded_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = '用户文件'
        verbose_name_plural = '用户文件'

    def __str__(self):
        return f"{self.user.username} - {self.original_name}"

    def get_file_type(self):
        ext = os.path.splitext(self.original_name)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif']:
            return 'image'
        elif ext in ['.pdf', '.doc', '.docx', '.txt']:
            return 'document'
        elif ext in ['.mp4', '.avi', '.mov']:
            return 'video'
        return 'other'

    def save(self, *args, **kwargs):
        if not self.file_type:
            self.file_type = self.get_file_type()
        if not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def get_file_size_display(self):
        """返回人类可读的文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.file_size < 1024:
                return f"{self.file_size:.1f} {unit}"
            self.file_size /= 1024
        return f"{self.file_size:.1f} TB"

    def get_icon_class(self):
        """返回文件类型对应的图标类名"""
        icon_map = {
            'image': 'fa-image',
            'document': 'fa-file-alt',
            'video': 'fa-video',
            'other': 'fa-file'
        }
        return icon_map.get(self.file_type, 'fa-file')
