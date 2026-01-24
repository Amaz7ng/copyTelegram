from rest_framework import serializers
from .models import ChatMember, Message, Chat
import os

class MessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.ReadOnlyField(source='sender.username')
    sender_prefix = serializers.SerializerMethodField()
    chat = serializers.PrimaryKeyRelatedField(
        queryset=Chat.objects.all(), 
        required=False, 
        allow_null=True
    )
    
    class Meta:
        model = Message
        fields = ['id', 'chat', 'sender_username', 
                  'sender_prefix', 'text', 'file', 'file_type', 'reply_to', 'created_at']
    
    def get_sender_prefix(self, obj):
        member = ChatMember.objects.filter(chat=obj.chat, user=obj.sender).first()
        return member.custom_title if member else None
    
    def get_file(self, obj):
        if obj.file:
            return os.path.basename(obj.file.name)
        return None
    
    
class ChatListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    interlocutor = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'type', 'title', 'last_message', 'interlocutor']

    def get_last_message(self, obj):
        if obj.last_message_link:
            return MessageSerializer(obj.last_message_link).data
        return None
    
    def get_interlocutor(self, obj):
        if obj.type == Chat.DIRECT:

            user = self.context['request'].user
            member = obj.members.exclude(user=user).first()
            return member.user.username if member else "Удаленный аккаунт"
        return None