from rest_framework import serializers
from .models import ChatMember, Message, Chat


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
    
    
class ChatListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    interlocutor = serializers.SerializerMethodField()

    class Meta:
        model = Chat
        fields = ['id', 'type', 'title', 'last_message', 'interlocutor']

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        return MessageSerializer(last_msg).data if last_msg else None

    def get_interlocutor(self, obj):
        if obj.type == Chat.DIRECT:

            user = self.context['request'].user
            member = obj.members.exclude(user=user).first()
            return member.user.username if member else "Удаленный аккаунт"
        return None