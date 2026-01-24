from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Message, Chat, ChatMember, User
from .serializers import MessageSerializer, ChatListSerializer
from .services import get_or_create_direct_chat, repost_to_discussion
import requests

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """
        Фильтруем сообщения по чату. 
        Если ID чата не передан, возвращаем пустой список, чтобы не грузить лишнее.
        """
        chat_id = self.request.query_params.get('chat')
        if not chat_id:
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

        if chat.type == Chat.CHANNEL and chat.discussion_group:
            repost_to_discussion(message, chat.discussion_group)

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    

class ChatViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет для просмотра списка чатов пользователя (Inbox).
    """
    serializer_class = ChatListSerializer 	
    permission_classes = [IsAuthenticated]

    def get_queryset(self):     
        chat_id = self.request.query_params.get('chat')
        user = self.request.user
        
        if not chat_id:
            return Message.objects.none()
        
        is_member = ChatMember.objects.filter(chat_id=chat_id, user=user).exists()
        is_creator = Chat.objects.filter(id=chat_id, creator=user).exists()
        
        if not is_member and not is_creator:
            return Message.objects.none()
        
        return Chat.objects.filter(members__user=self.request.user)\
            .prefetch_related('members__user', 'messages')\
            .order_by('-created_at')