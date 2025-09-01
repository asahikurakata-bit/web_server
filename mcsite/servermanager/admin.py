from django.contrib import admin
from .models import MinecraftServer

@admin.register(MinecraftServer)
class MinecraftServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan_type', 'port', 'is_active', 'cpu_cores', 'mem_limit', 'storage', 'backup_type')
    list_editable = ('is_active', 'cpu_cores', 'mem_limit')
    list_filter = ('is_active', 'plan_type', 'user')
    search_fields = ('user__username', 'port')
