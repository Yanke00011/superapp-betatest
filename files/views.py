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
    file_types = UserFile.FILE_TYPES
    
    # 添加文件统计
    stats = {
        'image': {'count': 0, 'size': 0},
        'document': {'count': 0, 'size': 0},
        'video': {'count': 0, 'size': 0},
        'other': {'count': 0, 'size': 0}
    }
    
    for file in files:
        stats[file.file_type]['count'] += 1
        stats[file.file_type]['size'] += file.file_size
    
    # 添加文件上传设置到上下文
    context = {
        'files': files,
        'file_types': file_types,
        'form': FileUploadForm(),
        'image_count': stats['image']['count'],
        'image_size': stats['image']['size'],
        'document_count': stats['document']['count'],
        'document_size': stats['document']['size'],
        'video_count': stats['video']['count'],
        'video_size': stats['video']['size'],
        'upload_settings_json': json.dumps({
            'allowed_types': settings.ALLOWED_FILE_TYPES,
            'max_size': settings.MAX_UPLOAD_SIZE,
            'max_size_mb': settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        })
    }
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
@require_POST
def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        file = request.FILES['file']
        # 检查存储配额
        quota = request.user.storage_quota
        if not quota.has_sufficient_space(file.size):
            return JsonResponse({
                'status': 'error',
                'message': '存储空间不足'
            })
        
        # 创建文件记录
        user_file = UserFile.objects.create(
            user=request.user,
            file=file,
            original_name=file.name,
            file_size=file.size
        )
        
        # 更新已使用的存储空间
        quota.update_used_storage(file.size)
        
        return JsonResponse({
            'status': 'success',
            'message': '文件上传成功',
            'file_id': user_file.id
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
    file = get_object_or_404(UserFile, id=file_id, user=request.user)
    file_size = file.file_size
    
    # 删除文件
    file.file.delete()
    file.delete()
    
    # 更新存储配额
    request.user.storage_quota.update_used_storage(-file_size)
    
    messages.success(request, '文件已删除')
    return redirect('file_list')
