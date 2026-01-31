from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    # --- ПОЛЯ-ЗЕРКАЛА (Синхронизируются через Kafka) ---
    # Мы убираем password из обязательных, так как аутентификация через токен
    # ID будет приходить из Kafka и перезаписывать локальный, если нужно
    
    search_handle = models.CharField(max_length=32, unique=True, db_index=True, null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True, null=True, verbose_name="О себе")
    avatar = models.CharField(max_length=500, blank=True, null=True, verbose_name="URL аватара")
    
    # Эти поля нужны, чтобы Django не требовал их при создании через консоль
    REQUIRED_FIELDS = ['email', 'search_handle']

    def __str__(self):
        return f"{self.username} ({self.id})"

class Chat(models.Model):
    GROUP = 'group'
    CHANNEL = 'channel'
    DIRECT = 'direct'
    CHAT_TYPES = [
        (GROUP, 'Группа'),
        (CHANNEL, 'Канал'),
        (DIRECT, 'Личная переписка'),
    ]
    type = models.CharField(max_length=10, choices=CHAT_TYPES, default=GROUP)
    title = models.CharField(max_length=255, blank=True, null=True)
    link_handle = models.CharField(max_length=32, unique=True, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    
    creator = models.ForeignKey(User, 
                                on_delete=models.CASCADE, 
                                related_name='created_chats',
                                null=True,
                                blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Ссылка на последнее сообщение для быстрого отображения в списке чатов
    last_message_link = models.ForeignKey(
        'Message', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='last_in_chats'
    )
    
    # Для привязки чата комментариев к каналу (как в ТГ)
    discussion_group = models.OneToOneField(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='linked_channel'
    )

    def __str__(self):
        return self.title if self.title else f"Chat {self.id} ({self.type})"

class ChatMember(models.Model):
    ADMIN = 'admin'
    MEMBER = 'member'
    
    ROLE_CHOICES = [
        (ADMIN, 'Администратор'),
        (MEMBER, 'Участник'),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_memberships')
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=MEMBER)
    
    # Права (Permissions)
    can_change_info = models.BooleanField(default=False)
    can_delete_messages = models.BooleanField(default=False)
    can_ban_users = models.BooleanField(default=False)
    can_invite_users = models.BooleanField(default=False)
    can_pin_messages = models.BooleanField(default=False)
    can_add_admins = models.BooleanField(default=False)
    
    custom_title = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name="Кастомный титул"
    )

    class Meta:
        unique_together = ('chat', 'user') # Один юзер в чате только один раз

    def __str__(self):
        return f"{self.user.username} -> {self.chat.title}"

class Message(models.Model):
    FILE_TYPES = [
        ('image', 'Фото'), 
        ('video', 'Видео'), 
        ('file', 'Файл'), 
        ('audio', 'Аудио')
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    
    text = models.TextField(blank=True, null=True)
    
    # Файлы храним либо как путь, либо как ссылку на Media Service
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, blank=True, null=True)
    
    # Для лички это работает, для групп нужна отдельная таблица MessageReadStatus
    is_read = models.BooleanField(default=False)
    
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='replies'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) # Добавил дату изменения
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at'] # Свежие сообщения первыми (удобно для пагинации)

    def save(self, *args, **kwargs):   
        is_new = self.id is None
        super().save(*args, **kwargs)
        
        # Обновляем ссылку на последнее сообщение в чате
        if is_new:
            self.chat.last_message_link = self
            self.chat.save(update_fields=['last_message_link'])

    def __str__(self):
        preview = self.text[:20] if self.text else f"[{self.file_type}]"
        return f"{self.sender.username}: {preview}"