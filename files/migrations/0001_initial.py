# Generated by Django 5.1.5 on 2025-01-28 05:55

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='users/%Y/%m/%d/')),
                ('file_type', models.CharField(choices=[('image', '图片'), ('document', '文档'), ('video', '视频'), ('other', '其他')], max_length=20)),
                ('original_name', models.CharField(max_length=255)),
                ('file_size', models.BigIntegerField()),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('description', models.TextField(blank=True)),
                ('is_public', models.BooleanField(default=False)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': '用户文件',
                'verbose_name_plural': '用户文件',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
