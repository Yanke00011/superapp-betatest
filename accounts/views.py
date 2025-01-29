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
        # 清除登录尝试记录
        cache.delete(f'login_attempts_{self.request.POST.get("phone_number")}')
        # 处理"记住我"功能
        if self.request.POST.get('remember_me'):
            self.request.session.set_expiry(1209600)  # 2周
        return super().form_valid(form)
    
    def form_invalid(self, form):
        phone_number = self.request.POST.get('phone_number')
        if phone_number:
            attempts = cache.get(f'login_attempts_{phone_number}', 0) + 1
            cache.set(f'login_attempts_{phone_number}', attempts, LOGIN_ATTEMPT_TIMEOUT)
            
            if attempts >= MAX_LOGIN_ATTEMPTS:
                form.add_error(None, f'登录尝试次数过多，请{LOGIN_ATTEMPT_TIMEOUT//60}分钟后再试')
                return self.render_to_response(self.get_context_data(form=form))
        
        return super().form_invalid(form)

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('home')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

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
            phone_number = form.cleaned_data['phone_number']
            birthday = form.cleaned_data['birthday']
            try:
                user = CustomUser.objects.get(
                    phone_number=phone_number,
                    birthday=birthday
                )
                # 验证成功，重定向到设置新密码页面
                request.session['reset_user_id'] = user.id
                return redirect('password_reset_confirm')
            except CustomUser.DoesNotExist:
                form.add_error(None, '未找到匹配的用户信息')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'accounts/password_reset_form.html', {'form': form})

def password_reset_confirm(request):
    user_id = request.session.get('reset_user_id')
    if not user_id:
        return redirect('password_reset_request')
    
    try:
        user = CustomUser.objects.get(id=user_id)
    except CustomUser.DoesNotExist:
        return redirect('password_reset_request')
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            # 清除session
            del request.session['reset_user_id']
            messages.success(request, '密码已重置，请使用新密码登录')
            return redirect('login')
    else:
        form = SetPasswordForm()
    
    return render(request, 'accounts/password_reset_confirm.html', {'form': form})

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
    
    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 创建用户的存储配额
            UserStorageQuota.objects.create(
                user=user,
                max_storage=settings.MAX_USER_STORAGE
            )
            login(request, user)
            messages.success(request, '账号创建成功！')
            return redirect('home')
        return render(request, self.template_name, {'form': form})

class WelcomeView(View):
    template_name = 'welcome.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name)