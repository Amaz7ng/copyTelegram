from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    search_handle = models.CharField(max_length=32, unique=True, db_index=True)
    
    REQUIRED_FIELDS = ['search_handle', 'email']

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
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(User, 
                                on_delete=models.CASCADE, 
                                related_name='created_chats',
                                null=True,
                                blank=True)
    
    last_message_link = models.ForeignKey(
        'Message', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='last_in_chats'
    )
    
    discussion_group = models.OneToOneField(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='linked_channel'
    )

    def __str__(self):
        return self.title if self.title else f"Direct Chat {self.id}"

class ChatMember(models.Model):
    ADMIN = 'admin'
    MEMBER = 'member'
    
    ROLE_CHOICES = [
        (ADMIN, 'Администратор'),
        (MEMBER, 'Участник'),
    ]

    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=MEMBER)
    
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
        verbose_name="Кастомный титул (префикс)"
    )

    can_manage_titles = models.BooleanField(
        default=False, 
        verbose_name="Может менять титулы другим"
    )

    class Meta:
        unique_together = ('chat', 'user')

    def __str__(self):
        return f"{self.user.username} in {self.chat.title} ({self.role})"
    
class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='messages')
    
    text = models.TextField(blank=True, null=True)
    
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    file_type = models.CharField(
        max_length=20, 
        choices=[('image', 'Фото'), ('video', 'Видео'), ('file', 'Файл'), ('link', 'Ссылка')],
        blank=True, null=True
    )
    is_read = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='replies'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    is_edited = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):   
        is_new = self.id is None
        
        super().save(*args, **kwargs)
        
        if is_new:
            chat = self.chat
            chat.last_message_link = self
            chat.save(update_fields=['last_message_link'])

    def __str__(self):
        if self.text:
            return f"{self.sender.username}: {self.text[:20]}"
        elif self.file:
            return f"{self.sender.username}: [Файл: {self.file_type}]"
        else:
            return f"{self.sender.username}: (пустое сообщение)"