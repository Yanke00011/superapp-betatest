from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser
from django.utils import timezone
from django.contrib.auth import authenticate
import uuid

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(  # Django AuthenticationForm 需要 username 字段
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入手机号码',
            'autocomplete': 'phone_number'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入密码',
            'autocomplete': 'current-password'
        })
    )

    error_messages = {
        'invalid_login': '手机号码或密码不正确。请注意密码区分大小写。',
        'inactive': '此账号已被禁用。',
    }

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            # 验证手机号码格式
            if not username.isdigit() or len(username) != 11 or not username.startswith('1'):
                raise ValidationError(
                    '请输入有效的手机号码（11位数字，以1开头）',
                    code='invalid_phone'
                )

            self.user_cache = authenticate(
                self.request, username=username, password=password
            )
            if self.user_cache is None:
                raise ValidationError(
                    self.error_messages['invalid_login'],
                    code='invalid_login',
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data

    def get_invalid_login_error(self):
        return ValidationError(
            self.error_messages['invalid_login'],
            code='invalid_login',
        )

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入邮箱'
        })
    )
    
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入用户名'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 移除默认的密码帮助文本
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None
        # 添加form-control类到密码字段
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请输入密码'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': '请确认密码'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('该邮箱已被注册')
        return email

class CustomUserChangeForm(UserChangeForm):
    password = None  # 移除密码字段，使用专门的密码修改表单

    class Meta:
        model = CustomUser
        fields = ('real_name', 'birthday', 'avatar')
        widgets = {
            'real_name': forms.TextInput(attrs={'class': 'form-control'}),
            'birthday': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'avatar': forms.FileInput(attrs={'class': 'form-control'})
        }

class PasswordResetRequestForm(forms.Form):
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入注册时的手机号码'
        })
    )
    birthday = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '请输入注册时的生日'
        })
    )

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
            return phone_number
        except CustomUser.DoesNotExist:
            raise ValidationError('该手机号码未注册')

class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入新密码'
        }),
        label='新密码'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请确认新密码'
        }),
        label='确认新密码'
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        if password1 and password2 and password1 != password2:
            raise ValidationError('两次输入的密码不一致')
        return cleaned_data