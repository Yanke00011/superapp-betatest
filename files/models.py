from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator, ValidationError
from django.utils import timezone
import os
import uuid

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

    def get_allowed_extensions(self):
        """根据文件类型返回允许的扩展名"""
        return settings.ALLOWED_FILE_TYPES.get(self.file_type, [])

    def get_upload_path(instance, filename):
        """为每个文件生成唯一的上传路径"""
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{ext}"
        return os.path.join('users', str(instance.user.id), instance.file_type, unique_filename)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(
        upload_to=get_upload_path,
        # 移除这个验证器，我们会在clean方法中处理验证
        # validators=[FileExtensionValidator(allowed_extensions=[])]
    )
    file_type = models.CharField(max_length=20, choices=FILE_TYPES)
    original_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
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

    def clean(self):
        if self.file:
            # 验证文件大小
            if self.file.size > settings.MAX_UPLOAD_SIZE:
                raise ValidationError(f'文件大小不能超过 {settings.MAX_UPLOAD_SIZE/1024/1024}MB')
            
            # 验证文件类型
            ext = os.path.splitext(self.file.name)[1][1:].lower()
            allowed_extensions = []
            for extensions in settings.ALLOWED_FILE_TYPES.values():
                allowed_extensions.extend(extensions)
            
            if ext not in allowed_extensions:
                raise ValidationError(f'不支持的文件类型。支持的类型：{", ".join(allowed_extensions)}')

    def save(self, *args, **kwargs):
        if not self.file_type:
            self.file_type = self.get_file_type()
        if not self.file_size:
            self.file_size = self.file.size
        self.full_clean()  # 在保存前进行验证
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

    def delete(self, *args, **kwargs):
        """重写删除方法以确保文件也被删除"""
        # 保存文件路径以便后续删除
        file_path = self.file.path if self.file else None
        
        # 更新用户存储配额
        if self.file_size:
            self.user.storage_quota.update_used_storage(-self.file_size)
        
        # 调用父类的删除方法
        super().delete(*args, **kwargs)
        
        # 删除物理文件
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
