from django import forms
from .models import UserFile

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UserFile
        fields = ['file', 'description', 'is_public']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '文件描述（可选）'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }