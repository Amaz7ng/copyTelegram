from django.conf import settings
from django.db import transaction
from asgiref.sync import async_to_sync
from rest_framework import viewsets, status
from rest_framework.response import Response
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from .models import Message, Chat, ChatMember, User
from utils.kafka_producer import send_notification_to_kafka
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import MessageSerializer, ChatListSerializer
from .services import get_or_create_direct_chat, repost_to_discussion
import requests
import threading
import os
from django.shortcuts import get_object_or_404
from django.conf import settings

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    # --- ВОТ ЭТОГО МЕТОДА У ТЕБЯ НЕ БЫЛО ---
    def broadcast_to_ws(self, chat_id, data):
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"chat_{chat_id}",
                {
                    "type": "chat_message",
                    "message": data
                }
            )
        except Exception as e:
            print(f"WebSocket Broadcast Error: {e}")

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat')         
        if not chat_id or not str(chat_id).isdigit():
            return Message.objects.none()
            
        return Message.objects.filter(
            chat_id=chat_id,
            chat__members__user=self.request.user 
        ).select_related('sender').order_by('created_at')

    def create(self, request, *args, **kwargs):
        chat_id = request.data.get('chat')
        receiver_id = request.data.get('receiver_id')
        file_obj = request.FILES.get('file')
        user = request.user
        
        # 1. Поиск/Создание чата
        if receiver_id and not chat_id:
            chat = get_or_create_direct_chat(user.id, receiver_id)
        else:
            chat = get_object_or_404(Chat, id=chat_id)

        # 2. Обработка медиа
        saved_file_name = None
        if file_obj:
            try:
                files = {'file': (file_obj.name, file_obj.file, file_obj.content_type)}
                media_url = "http://fastapi_media:8002/upload" 
                resp = requests.post(media_url, files=files, timeout=5)
                if resp.status_code == 200:
                    saved_file_name = resp.json().get('saved_as')
            except Exception as e:
                print(f"MEDIA SERVICE ERROR: {e}")
                return Response({"error": "Media service unavailable"}, status=503)

        # 3. Сохранение сообщения
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = serializer.save(
            sender=user, 
            chat=chat, 
            file=saved_file_name,
            file_type='image' if file_obj else None
        )
        
        # 4. Broadcast (Теперь метод существует!)
        self.broadcast_to_ws(chat.id, serializer.data)

        # 5. Kafka
        self.send_notifications(chat, user, message)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def send_notifications(self, chat, sender, message):
        try:
            # Получаем ID всех участников кроме отправителя
            member_ids = list(ChatMember.objects.filter(chat=chat).exclude(user=sender).values_list('user_id', flat=True))
            if member_ids:
                send_notification_to_kafka({
                    "user_ids": member_ids,
                    "chat_id": chat.id,
                    "type": "new_message",
                    "text": message.text[:50] if message.text else "Файл",
                    "sender_name": sender.username
                })
        except Exception as e:
            print(f"Kafka Error: {e}")

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatListSerializer   
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(members__user=self.request.user)\
            .select_related('last_message_link')\
            .prefetch_related('members__user')\
            .order_by('-created_at')

    def create(self, request, *args, **kwargs):
        chat_type = request.data.get('type', Chat.GROUP)
        title = request.data.get('title', 'Новый чат')
        user = request.user

        with transaction.atomic():
            # 1. Создаем сам чат
            chat = Chat.objects.create(
                type=chat_type,
                title=title,
                creator=user
            )
            # 2. Добавляем создателя как Админа
            ChatMember.objects.create(
                chat=chat,
                user=user,
                role=ChatMember.ADMIN
            )
        
        serializer = self.get_serializer(chat)
        return Response(serializer.data, status=status.HTTP_201_CREATED)