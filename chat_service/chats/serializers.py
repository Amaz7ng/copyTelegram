from rest_framework import serializers
from .models import ChatMember, Message, Chat
import os

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    sender_prefix = serializers.SerializerMethodField()
    # Указываем, что поле file теперь обрабатывается методом
    file = serializers.SerializerMethodField() 
    
    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender_username', 
                  'sender_prefix', 'text', 'file', 'file_type', 'reply_to', 'created_at']

    def get_sender_prefix(self, obj):
        member = ChatMember.objects.filter(chat=obj.chat, user=obj.sender).first()
        return member.custom_title if member else None

    def get_file(self, obj):
        if not obj.file:
            return None
        
        request = self.context.get('request')
        file_name = os.path.basename(obj.file.name)
        
        if request:
            return request.build_absolute_uri(f"/api/media/{file_name}")
        
        return f"/api/media/{file_name}"
    
    
class ChatListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)
    # Переопределяем title, чтобы он возвращал нормальное имя
    title = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'type', 'title', 'last_message', 'unread_count']

    def get_title(self, obj):
        # 1. Если это группа или канал и у них есть название — возвращаем его
        if obj.type in [Chat.GROUP, Chat.CHANNEL] and obj.title:
            return obj.title
        
        # 2. Если это личка (DIRECT), ищем собеседника
        request = self.context.get('request')
        user = request.user if request else self.context.get('user')

        if not user or user.is_anonymous:
            return obj.title or f"Чат {obj.id}"

        other_member = ChatMember.objects.filter(chat=obj).exclude(user=user).select_related('user').first()
        
        if other_member:
            return other_member.user.username
        
        return obj.title or "Заметки (Вы)"

    def get_last_message(self, obj):
        if obj.last_message_link:
            return MessageSerializer(obj.last_message_link, context=self.context).data
        return None