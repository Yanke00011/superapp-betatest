from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import PermissionDenied
from .models import UserFile, UserStorageQuota
from .forms import FileUploadForm
import os
from django.conf import settings
import mimetypes
import json
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.contrib import messages
from django.core.cache import cache
from django.db import transaction
from django.core.exceptions import ValidationError
import uuid
import logging

# Create your views here.

@login_required
def file_list(request):
    # 确保用户有存储配额记录
    storage_quota, created = UserStorageQuota.objects.get_or_create(
        user=request.user,
        defaults={'max_storage': settings.MAX_USER_STORAGE}
    )
    
    # 获取当前用户的所有文件
    files = UserFile.objects.filter(user=request.user)
    
    context = {
        'files': files,
        'file_types': UserFile.FILE_TYPES,
        'max_upload_size': settings.MAX_UPLOAD_SIZE,
        'allowed_file_types': json.dumps(settings.ALLOWED_FILE_TYPES),
        'storage_quota': storage_quota,
    }
    
    # 打印调试信息
    print("Upload configuration:", {
        'max_upload_size': settings.MAX_UPLOAD_SIZE,
        'allowed_file_types': settings.ALLOWED_FILE_TYPES,
    })
    
    return render(request, 'files/file_list.html', context)

class FileListView(LoginRequiredMixin, ListView):
    model = UserFile
    template_name = 'files/file_list.html'
    context_object_name = 'files'
    
    def get_queryset(self):
        return UserFile.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_files = self.get_queryset()
        
        # 获取不同类型文件的统计信息
        context['image_count'] = user_files.filter(file_type='image').count()
        context['document_count'] = user_files.filter(file_type='document').count()
        context['video_count'] = user_files.filter(file_type='video').count()
        
        context['image_size'] = user_files.filter(file_type='image').aggregate(Sum('file_size'))['file_size__sum'] or 0
        context['document_size'] = user_files.filter(file_type='document').aggregate(Sum('file_size'))['file_size__sum'] or 0
        context['video_size'] = user_files.filter(file_type='video').aggregate(Sum('file_size'))['file_size__sum'] or 0
        
        return context

@login_required
def upload_progress(request):
    """获取文件上传进度"""
    if 'X-Progress-ID' in request.GET:
        progress_id = request.GET['X-Progress-ID']
        cache_key = f'upload_progress_{progress_id}'
        data = cache.get(cache_key, {})
        return JsonResponse(data)
    return JsonResponse({'error': 'Progress ID not found'})

@login_required
@transaction.atomic
def upload_file(request):
    if request.method == 'POST':
        try:
            if 'file' not in request.FILES:
                return JsonResponse({
                    'status': 'error',
                    'message': '没有接收到文件'
                })

            file = request.FILES['file']
            user = request.user
            
            # 检查存储配额
            quota, created = UserStorageQuota.objects.get_or_create(
                user=user,
                defaults={'max_storage': settings.MAX_USER_STORAGE}
            )
            
            if not quota.has_sufficient_space(file.size):
                return JsonResponse({
                    'status': 'error',
                    'message': '存储空间不足'
                })
            
            # 获取文件类型
            ext = os.path.splitext(file.name)[1][1:].lower()
            file_type = None
            
            # 检查文件类型
            for type_key, extensions in settings.ALLOWED_FILE_TYPES.items():
                if ext in extensions:
                    file_type = type_key
                    break
            
            if not file_type:
                allowed_types = []
                for extensions in settings.ALLOWED_FILE_TYPES.values():
                    allowed_types.extend(extensions)
                return JsonResponse({
                    'status': 'error',
                    'message': f'不支持的文件类型。支持的类型：{", ".join(allowed_types)}'
                })
            
            # 确保用户目录存在
            user_dir = os.path.join(settings.MEDIA_ROOT, 'users', str(user.id), file_type)
            os.makedirs(user_dir, exist_ok=True)
            
            # 创建文件记录
            user_file = UserFile.objects.create(
                user=user,
                file=file,
                file_type=file_type,
                original_name=file.name,
                file_size=file.size
            )
            
            # 更新存储配额
            quota.update_used_storage(file.size)
            
            return JsonResponse({
                'status': 'success',
                'message': '文件上传成功',
                'file': {
                    'id': user_file.id,
                    'name': user_file.original_name,
                    'size': user_file.get_file_size_display(),
                    'type': user_file.file_type
                }
            })
            
        except Exception as e:
            import traceback
            print('Upload error:', str(e))
            print(traceback.format_exc())
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': '无效的请求'})

@login_required
def download_file(request, file_id):
    file = get_object_or_404(UserFile, id=file_id, user=request.user)
    response = FileResponse(file.file)
    response['Content-Disposition'] = f'attachment; filename="{file.original_name}"'
    return response

@login_required
@require_POST
def delete_file(request, file_id):
    try:
        file = get_object_or_404(UserFile, id=file_id, user=request.user)
        file_size = file.file_size
        
        # 删除文件
        file.delete()
        
        # 更新存储配额
        quota = request.user.storage_quota
        quota.update_used_storage(-file_size)
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
