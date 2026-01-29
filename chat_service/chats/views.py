from django.conf import settings
from django.db import transaction
from asgiref.sync import async_to_sync
from rest_framework import viewsets, status
from rest_framework.response import Response
from channels.layers import get_channel_layer
from .models import Message, Chat, ChatMember, User
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import MessageSerializer, ChatListSerializer
from .services import get_or_create_direct_chat, repost_to_discussion
import requests

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat')     
        if not chat_id or not str(chat_id).isdigit():
            return Message.objects.none()
            
        return Message.objects.filter(chat_id=chat_id)\
                             .select_related('sender')\
                             .order_by('created_at')
                             
                             
    def create(self, request, *args, **kwargs):
        chat_id = request.data.get('chat')
        receiver_id = request.data.get('receiver_id')
        file_obj = request.FILES.get('file')
        user = request.user
        
        if receiver_id and not chat_id:
            try:
                receiver = User.objects.get(id=receiver_id)
                chat = get_or_create_direct_chat(user, receiver)
                chat_id = chat.id
            except User.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                chat = Chat.objects.get(id=chat_id)
            except Chat.DoesNotExist:
                return Response({"error": "Чат не найден"}, status=status.HTTP_404_NOT_FOUND)

        member, created = ChatMember.objects.get_or_create(
            chat=chat, 
            user=user, 
            defaults={'role': ChatMember.MEMBER}
        )

        if chat.type == Chat.CHANNEL:
            is_creator = (chat.creator == user)
            is_admin = (member.role == ChatMember.ADMIN)
            if not (is_creator or is_admin):
                return Response({"error": "Только админы могут писать в канал"}, status=status.HTTP_403_FORBIDDEN)
            
        saved_file_name = None
        if file_obj:
            try:
                files = {'file': (file_obj.name, file_obj.file, file_obj.content_type)}
                media_url = getattr(settings, 'MEDIA_SERVICE_URL', "http://fastapi_media:8002/upload")
                resp = requests.post(media_url, files=files, timeout=10)
                
                if resp.status_code == 200:
                    media_data = resp.json()
                    saved_file_name = media_data.get('saved_as') 
                else:
                    return Response({"error": "Ошибка медиа-сервиса"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except requests.exceptions.RequestException as e:
                return Response({"error": f"Media Service недоступен: {str(e)}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = serializer.save(
            sender=user, 
            chat=chat, 
            file=saved_file_name,
            file_type='image' if file_obj else None
        )
        
        file_url = f"/api/media/{saved_file_name}" if saved_file_name else None
        
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"chat_{chat.id}",
            {
                "type": "chat_message",
                "message": message.text,
                "sender_username": user.username,
                "sender_id": user.id,
                "message_id": message.id,
                "file": file_url, # ТЕПЕРЬ КАРТИНКА ПРИЛЕТИТ СРАЗУ
            }
        )

        if chat.type == Chat.CHANNEL and chat.discussion_group:
            repost_to_discussion(message, chat.discussion_group)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

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