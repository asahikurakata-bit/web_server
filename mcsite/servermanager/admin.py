from django.contrib import admin
from .models import MinecraftServer

@admin.register(MinecraftServer)
class MinecraftServerAdmin(admin.ModelAdmin):
    # ★ 'server_type' を 'plan_type' に変更し、新しいフィールドも追加
    list_display = ('id', 'user', 'plan_type', 'port', 'is_active', 'cpu_cores', 'mem_limit', 'storage', 'backup_type')
    
    # list_displayに含まれるフィールドは編集可能にできる
    list_editable = ('is_active', 'cpu_cores', 'mem_limit')
    
    # ★ 'server_type' を 'plan_type' に変更
    list_filter = ('is_active', 'plan_type', 'user')
    
    # 検索機能
    search_fields = ('user__username', 'port')