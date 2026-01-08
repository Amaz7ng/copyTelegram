from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Message, Chat, ChatMember, User
from .serializers import MessageSerializer, ChatListSerializer
from .services import get_or_create_direct_chat, repost_to_discussion

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        chat_id = self.request.query_params.get('chat')
        return Message.objects.filter(chat_id=chat_id)\
                              .select_related('sender')\
                              .order_by('created_at')

    def create(self, request, *args, **kwargs):
        chat_id = request.data.get('chat')
        receiver_id = request.data.get('receiver_id')
        user = request.user
        
        if receiver_id and not chat_id:
            try:
                receiver = User.objects.get(id=receiver_id)
                chat = get_or_create_direct_chat(user, receiver)
                chat_id = chat.id
            except User.DoesNotExist:
                return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            chat = Chat.objects.get(id=chat_id)
        except Chat.DoesNotExist:
            return Response({"error": "Чат не найден"}, status=status.HTTP_404_NOT_FOUND)

        member = ChatMember.objects.filter(chat=chat, user=user).first()
        is_creator = (chat.creator == user)
        
        if not member and not is_creator:
            return Response({"error": "Вы не участник этого чата"}, status=status.HTTP_403_FORBIDDEN)

        if chat.type == Chat.CHANNEL:
            is_admin = (member and member.role == ChatMember.ADMIN)
            if not (is_creator or is_admin):
                return Response({"error": "Только админы могут писать в канал"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=user, chat=chat)

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