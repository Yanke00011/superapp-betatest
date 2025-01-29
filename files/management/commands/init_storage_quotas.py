from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from files.models import UserStorageQuota

class Command(BaseCommand):
    help = '为所有用户初始化存储配额'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        users = User.objects.all()
        created_count = 0
        
        for user in users:
            quota, created = UserStorageQuota.objects.get_or_create(
                user=user
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'成功为 {created_count} 个用户创建存储配额')
        ) 