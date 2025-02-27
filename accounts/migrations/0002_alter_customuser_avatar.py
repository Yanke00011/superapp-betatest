# Generated by Django 5.1.5 on 2025-01-28 05:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='avatar',
            field=models.ImageField(blank=True, help_text='用户头像', null=True, upload_to='avatars/%Y/%m/%d/', verbose_name='头像'),
        ),
    ]
