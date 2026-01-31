from django.contrib import admin
from .models import User, Chat, ChatMember, Message

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'search_handle', 'email', 'is_staff')
    search_fields = ('username', 'search_handle', 'email') # Нужен для autocomplete в других моделях
    list_filter = ('is_staff', 'is_superuser')

@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'type', 'creator', 'created_at')
    # Добавляем search_fields, чтобы работал autocomplete_fields
    search_fields = ('title', 'creator__username', 'link_handle') 
    autocomplete_fields = ['discussion_group', 'creator'] # Creator тоже удобно выбирать через поиск
    list_filter = ('type', 'created_at')

@admin.register(ChatMember)
class ChatMemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'chat', 'role', 'custom_title', 'can_add_admins')
    search_fields = ('user__username', 'chat__title', 'custom_title')
    list_filter = ('role', 'chat')
    # Добавляем autocomplete, чтобы не грузить выпадающий список из 1000 юзеров
    autocomplete_fields = ['user', 'chat']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'chat', 'role', 'custom_title')
        }),
        ('Разрешения (Permissions)', {
            'fields': (
                'can_change_info', 
                'can_delete_messages', 
                'can_ban_users', 
                'can_invite_users', 
                'can_pin_messages', 
                'can_add_admins', 
                'can_manage_titles'
            )
        }),
    )
    
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'chat', 'get_short_text', 'file_type', 'created_at')
    list_filter = ('file_type', 'created_at', 'chat')
    search_fields = ('text', 'sender__username')
    readonly_fields = ('created_at',)
    autocomplete_fields = ['sender', 'chat', 'reply_to'] # Важно для удобства

    def get_short_text(self, obj):
        return obj.text[:30] if obj.text else "[Файл/Медиа]"
    get_short_text.short_description = 'Текст'