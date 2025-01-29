# Generated by Django 5.1.5 on 2025-01-28 11:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0002_userstoragequota'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='userstoragequota',
            options={},
        ),
        migrations.AddField(
            model_name='userstoragequota',
            name='used_storage',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='userstoragequota',
            name='max_storage',
            field=models.BigIntegerField(default=104857600),
        ),
    ]
