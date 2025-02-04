from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, UpdateView
from .forms import CustomUserCreationForm, CustomUserChangeForm, PasswordResetRequestForm, CustomAuthenticationForm, SetPasswordForm
from .models import CustomUser
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.files.base import ContentFile
from PIL import Image
from io import BytesIO
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.core.cache import cache
from django.conf import settings
import os
from django.views.generic import View
from files.models import UserStorageQuota
from django.db import transaction
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.utils import timezone
from datetime import datetime, timedelta
import uuid

# 添加登录尝试限制
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_TIMEOUT = 300  # 5分钟

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('home')  # 修改为重定向到home
    
    def form_valid(self, form):
        # 添加登录限制
        username = form.cleaned_data.get('username')
        cache_key = f'login_attempts_{username}'
        attempts = cache.get(cache_key, 0)
        
        if attempts >= 5:  # 限制登录尝试次数
            form.add_error(None, '登录尝试次数过多，请15分钟后再试')
            return self.form_invalid(form)
            
        if not form.is_valid():
            cache.set(cache_key, attempts + 1, 900)  # 15分钟过期
            return self.form_invalid(form)
            
        cache.delete(cache_key)  # 登录成功后清除计数
        return super().form_valid(form)

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                # 创建用户
                user = form.save()
                
                # 创建用户目录
                user_media_path = os.path.join(settings.MEDIA_ROOT, f'users/{user.id}')
                os.makedirs(user_media_path, exist_ok=True)
                
                # 自动登录
                login(self.request, user)
                
                messages.success(self.request, '注册成功！')
                return redirect(self.success_url)
        except Exception as e:
            messages.error(self.request, f'注册失败：{str(e)}')
            return self.form_invalid(form)

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            if 'avatar' in request.FILES:
                image = Image.open(request.FILES['avatar'])
                # 统一图片格式为JPEG
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                # 调整图片大小
                image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                # 保存处理后的图片
                output = BytesIO()
                image.save(output, format='JPEG', quality=85)
                output.seek(0)
                
                # 确保用户目录存在
                request.user.create_user_directories()
                
                # 使用用户专属路径
                avatar_path = request.user.get_avatar_upload_path(request.FILES['avatar'].name)
                
                # 删除旧头像
                if request.user.avatar:
                    try:
                        old_avatar_path = request.user.avatar.path
                        if os.path.exists(old_avatar_path):
                            os.remove(old_avatar_path)
                    except Exception as e:
                        print(f"删除旧头像失败: {e}")
                
                # 保存新头像
                request.user.avatar.save(
                    os.path.basename(avatar_path),
                    ContentFile(output.read()),
                    save=False
                )
            form.save()
            messages.success(request, '个人资料已更新')
            return redirect('profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            # 将用户ID存储在session中
            request.session['reset_user_id'] = user.id
            request.session['reset_token'] = str(uuid.uuid4())
            request.session['reset_timestamp'] = str(timezone.now())
            return redirect('password_reset_confirm')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'accounts/password_reset_form.html', {'form': form})

def password_reset_confirm(request):
    # 验证session中的重置信息
    user_id = request.session.get('reset_user_id')
    reset_token = request.session.get('reset_token')
    reset_timestamp = request.session.get('reset_timestamp')
    
    if not all([user_id, reset_token, reset_timestamp]):
        messages.error(request, '密码重置链接无效或已过期')
        return redirect('password_reset_request')
    
    try:
        # 验证重置时间戳（15分钟有效期）
        timestamp = datetime.fromisoformat(reset_timestamp)
        if timezone.now() - timestamp > timedelta(minutes=15):
            raise ValueError('重置链接已过期')
        
        user = CustomUser.objects.get(id=user_id)
    except (ValueError, CustomUser.DoesNotExist):
        messages.error(request, '密码重置链接无效或已过期')
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            # 设置新密码
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            
            # 清除session
            for key in ['reset_user_id', 'reset_token', 'reset_timestamp']:
                request.session.pop(key, None)
            
            messages.success(request, '密码已重置成功，请使用新密码登录')
            return redirect('login')
    else:
        form = SetPasswordForm()
    
    return render(request, 'accounts/password_reset_confirm.html', {
        'form': form,
        'user': user
    })

@login_required
def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, '您已安全退出')
        return redirect('login')
    return render(request, 'accounts/logout.html')

# 监听退出登录信号
@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    # 清除用户相关的session和缓存
    request.session.flush()
    if user:
        cache.delete(f'user_data_{user.id}')

@login_required
def home_view(request):
    return render(request, 'home.html')

class RegisterView(View):
    template_name = 'accounts/signup.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        form = CustomUserCreationForm()
        return render(request, self.template_name, {'form': form})
    
    @transaction.atomic  # 添加事务支持
    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                # 创建用户存储配额
                UserStorageQuota.objects.create(
                    user=user,
                    max_storage=settings.MAX_USER_STORAGE
                )
                # 创建用户目录
                user_media_path = os.path.join(settings.MEDIA_ROOT, f'users/{user.id}')
                os.makedirs(user_media_path, exist_ok=True)
                
                login(request, user)
                return redirect('home')
        return render(request, self.template_name, {'form': form})

class WelcomeView(View):
    template_name = 'welcome.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name)

    def handle_no_permission(self):
        return redirect('login')

def bad_request(request, exception):
    return render(request, 'errors/400.html', status=400)

def permission_denied(request, exception):
    return render(request, 'errors/403.html', status=403)

def page_not_found(request, exception):
    return render(request, 'errors/404.html', status=404)

def server_error(request):
    return render(request, 'errors/500.html', status=500)

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='手机号码', help_text='请输入注册时使用的手机号码')