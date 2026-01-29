import json
import asyncio
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Chat, ChatMember
from .serializers import MessageSerializer
from utils.kafka_producer import send_notification_to_kafka

# Подключение к Redis для работы с уведомлениями
r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        # 1. Сначала определяем ID чата
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f"chat_{self.chat_id}"
        # 2. Обязательно определяем группу пользователя (для уведомлений)
        self.user_group_name = f"user_{self.user.id if self.user.is_authenticated else 'anonymous'}"

        if not self.user.is_authenticated:
            print(f"DEBUG: Rejecting connection for anonymous user")
            await self.close()
            return

        # 3. Добавляем в группы
        await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        
        await self.accept()

    async def disconnect(self, close_code):
        # Уведомляем чат об уходе (offline), если пользователь был в чате
        if hasattr(self, 'chat_group_name'):
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "user_status",
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "status": "offline"
                }
            )
            await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)

        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        # 1. Вход в чат и загрузка истории
        if action == 'join_chat':
            chat_id = data.get('chat_id')
            
            if await self.is_chat_member(chat_id):
                # Если уже был в другом чате — выходим из старой группы
                if hasattr(self, 'chat_group_name'):
                    await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)

                self.chat_id = chat_id
                self.chat_group_name = f"chat_{chat_id}"
                
                await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
                
                # Рассылаем статус Online
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        "type": "user_status",
                        "user_id": self.user.id,
                        "username": self.user.username,
                        "status": "online"
                    }
                )
                
                # Загружаем историю
                history = await self.get_chat_history(chat_id)
                await self.send(text_data=json.dumps({
                    'type': 'chat_history',
                    'messages': history
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Доступ запрещен'
                }))

        # 2. Статус "Печатает..."
        elif action == 'typing':
            if hasattr(self, 'chat_group_name'):
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        "type": "user_typing",
                        "username": self.user.username,
                        "is_typing": data.get('is_typing')
                    }
                )

        # 3. Прочтение сообщений
        elif action == 'mark_read':
            chat_id = data.get('chat_id')
            await self.mark_messages_as_read(chat_id)
            r.set(f"unread_count:{self.user.id}", 0)
            
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "messages_read_event",
                    "chat_id": chat_id,
                    "reader_id": self.user.id
                }
            )

    # --- ОБРАБОТЧИКИ СОБЫТИЙ ГРУПП (отправка на фронтенд) ---

    async def chat_message(self, event):
    # Убедись, что ключ называется именно 'sender_username', как ждет фронт
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_username': event.get('sender_username'), # Должно приходить извне
            'sender_id': event['sender_id'],
            'file': event.get('file'), 
            'message_id': event.get('message_id'),
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'user_id': event['user_id'],
            'username': event['username'],
            'status': event['status']
        }))

    async def user_typing(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_update',
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def messages_read_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'chat_id': event['chat_id'],
            'reader_id': event['reader_id']
        }))

    async def unread_badge_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'unread_badge',
            'unread_count': event['unread_count']
        }))

    # --- DATABASE OPERATIONS ---

    @database_sync_to_async
    def is_chat_member(self, chat_id):
        return ChatMember.objects.filter(chat_id=chat_id, user=self.user).exists()

    @database_sync_to_async
    def get_chat_history(self, chat_id, offset=0):
        messages = Message.objects.filter(chat_id=chat_id).select_related('sender').order_by('-created_at')[offset:offset+50]
    # Добавляем context={'request': None}, чтобы сериализатор не упал при поиске домена
        return MessageSerializer(list(reversed(messages)), many=True, context={'request': None}).data
    
    
    @database_sync_to_async
    def mark_messages_as_read(self, chat_id):
        Message.objects.filter(chat_id=chat_id, is_read=False).exclude(sender=self.user).update(is_read=True)