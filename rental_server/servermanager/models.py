from django.db import models
from django.contrib.auth.models import User

class MinecraftServer(models.Model):
    SERVER_TYPE_CHOICES = [
        ('java', 'Java Edition'),
        ('be', 'Bedrock Edition'),
        ('web', 'Web Hosting'),
    ]

    port = models.IntegerField(unique=True)
    is_active = models.BooleanField(default=False)
    cpu_cores = models.IntegerField(default=1)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)
    container_id = models.CharField(max_length=255, blank=True, null=True)
    mem_limit = models.CharField(max_length=10, default="2g")

    plan_type = models.CharField(max_length=10, choices=SERVER_TYPE_CHOICES, default='web', verbose_name='プランタイプ')
    storage = models.CharField(max_length=50, blank=True, null=True, verbose_name='ディスク容量')
    backup_type = models.CharField(max_length=50, blank=True, null=True, verbose_name='バックアップタイプ')

    mods = models.TextField(blank=True, default='', help_text='CurseForgeのFile IDをカンマ区切りで入力してください。', verbose_name='導入MOD (CurseForge File IDs)')
    world_data_path = models.CharField(max_length=255, blank=True, null=True, verbose_name='ワールドデータパス')
    version = models.CharField(max_length=20, default='LATEST', verbose_name='サーバーバージョン')

    def __str__(self):
        return f"Server for {self.user.username} ({self.get_plan_type_display()})"
