# Generated by Django 5.1.5 on 2025-02-01 07:26

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_customuser_birthday_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='customuser',
            name='accounts_cu_usernam_ab560e_idx',
        ),
        migrations.RemoveIndex(
            model_name='customuser',
            name='accounts_cu_email_5ce40b_idx',
        ),
        migrations.AlterField(
            model_name='customuser',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='avatars/', verbose_name='头像'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='birthday',
            field=models.DateField(blank=True, null=True, verbose_name='出生日期'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='phone_number',
            field=models.CharField(max_length=11, unique=True, validators=[django.core.validators.RegexValidator(message='请输入有效的手机号码（11位数字，以1开头）', regex='^1[3-9]\\d{9}$')], verbose_name='手机号码'),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='real_name',
            field=models.CharField(blank=True, max_length=50, verbose_name='真实姓名'),
        ),
    ]
