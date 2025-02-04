from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser
from django.utils import timezone
from django.contrib.auth import authenticate
import uuid
from django.core.validators import RegexValidator

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
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入手机号码'
        }),
        validators=[
            RegexValidator(
                regex=r'^1[3-9]\d{9}$',
                message='请输入有效的手机号码（11位数字，以1开头）'
            )
        ]
    )
    
    real_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入真实姓名'
        })
    )
    
    birthday = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入邮箱'
        })
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'phone_number', 'real_name', 'birthday', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        
        self.fields['username'].widget.attrs.update({
            'placeholder': '请输入用户名'
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': '请输入密码'
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': '请确认密码'
        })

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if CustomUser.objects.filter(phone_number=phone_number).exists():
            raise ValidationError('该手机号码已被注册')
        return phone_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.phone_number = self.cleaned_data['phone_number']
        user.real_name = self.cleaned_data['real_name']
        user.birthday = self.cleaned_data['birthday']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'phone_number', 'real_name', 'birthday', 'avatar')

class PasswordResetRequestForm(forms.Form):
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入注册时的手机号码'
        }),
        validators=[
            RegexValidator(
                regex=r'^1[3-9]\d{9}$',
                message='请输入有效的手机号码（11位数字，以1开头）'
            )
        ]
    )
    birthday = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': '请输入注册时的生日'
        }),
        error_messages={
            'required': '请输入出生日期',
            'invalid': '请输入有效的日期格式'
        }
    )

    def clean(self):
        cleaned_data = super().clean()
        phone_number = cleaned_data.get('phone_number')
        birthday = cleaned_data.get('birthday')

        if phone_number and birthday:
            try:
                user = CustomUser.objects.get(
                    phone_number=phone_number,
                    birthday=birthday
                )
                cleaned_data['user'] = user
            except CustomUser.DoesNotExist:
                raise ValidationError('手机号码或出生日期不正确，请重新输入')
        return cleaned_data

class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请输入新密码'
        }),
        min_length=8,
        error_messages={
            'min_length': '密码长度至少为8个字符',
            'required': '请输入新密码'
        }
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': '请确认新密码'
        }),
        error_messages={
            'required': '请再次输入新密码'
        }
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2:
            if password1 != password2:
                raise ValidationError('两次输入的密码不一致')
            
            # 密码复杂度验证
            if not any(char.isdigit() for char in password1):
                raise ValidationError('密码必须包含数字')
            if not any(char.isalpha() for char in password1):
                raise ValidationError('密码必须包含字母')
        return cleaned_data