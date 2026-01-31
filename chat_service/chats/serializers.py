from rest_framework import serializers
from .models import ChatMember, Message, Chat
import os

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    sender_prefix = serializers.SerializerMethodField()
    file = serializers.SerializerMethodField() 
    
    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender_username', 
                  'sender_prefix', 'text', 'file', 'file_type', 'reply_to', 'created_at']

    def get_sender_prefix(self, obj):
        # Оптимизация запроса титула
        member = ChatMember.objects.filter(chat_id=obj.chat_id, user_id=obj.sender_id).only('custom_title').first()
        return member.custom_title if member else None

    def get_file(self, obj):
        if not obj.file:
            return None
        
        # КОСТЫЛЬ/ФИКС: Берем только имя файла и жестко прописываем путь для Nginx.
        # Это решит проблему двойных путей (/api/media/api/media...)
        file_name = os.path.basename(str(obj.file))
        
        # Возвращаем путь, который ожидает Nginx proxy
        # Nginx перехватит /api/media/ и отправит запрос в Minio/FastAPI
        return f"/api/media/{file_name}"
    
class ChatListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)
    title = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'type', 'title', 'last_message', 'unread_count']

    def get_title(self, obj):
        if obj.type in [Chat.GROUP, Chat.CHANNEL] and obj.title:
            return obj.title
        
        request = self.context.get('request')
        user = request.user if request else self.context.get('user')

        if not user or user.is_anonymous:
            return obj.title or f"Чат {obj.id}"

        other_member = obj.members.exclude(user=user).select_related('user').first()
        
        if other_member:
            return other_member.user.username
        
        return "Заметки (Вы)"

    def get_last_message(self, obj):
        if obj.last_message_link:
            return MessageSerializer(obj.last_message_link, context=self.context).data
        return None