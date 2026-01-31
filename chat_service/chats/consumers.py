import json
import asyncio
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Chat, ChatMember
from .serializers import MessageSerializer
from utils.kafka_producer import send_notification_to_kafka

r = redis.Redis(host='redis', port=6379, db=1, decode_responses=True)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        
        self.chat_id = self.scope['url_route']['kwargs'].get('chat_id')
        if self.chat_id:
            self.chat_group_name = f"chat_{self.chat_id}"
            await self.channel_layer.group_add(self.chat_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'chat_group_name'):
            await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)
        await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get('action')

            if action == 'join_chat':
                await self.handle_join_chat(data.get('chat_id'))
            elif action == 'send_message':
                await self.handle_send_message(data)
            elif action == 'typing':
                await self.handle_typing(data.get('is_typing'))
            elif action == 'mark_read':
                await self.handle_mark_read(data.get('chat_id'))
        except Exception as e:
            print(f"WS RECEIVE ERROR: {e}")

    # --- ЛОГИКА ---

    async def handle_join_chat(self, chat_id):
        if await self.is_chat_member(chat_id):
            if hasattr(self, 'chat_group_name'):
                await self.channel_layer.group_discard(self.chat_group_name, self.channel_name)

            self.chat_id = chat_id
            self.chat_group_name = f"chat_{chat_id}"
            await self.channel_layer.group_add(self.chat_group_name, self.channel_name)

            history = await self.get_chat_history(chat_id)
            await self.send(text_data=json.dumps({
                'type': 'chat_history',
                'messages': history
            }))
        else:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'Forbidden'}))

    async def handle_send_message(self, data):
        chat_id = data.get('chat_id') or self.chat_id
        text = data.get('message')

        if not chat_id:
            return

        asyncio.create_task(self.process_message_background(chat_id, text))
        
    async def process_message_background(self, chat_id, text):
        try:
            message_obj, serializer_data = await self.save_message_to_db(chat_id, text)

            if message_obj:
                # FIX: Используем ключ "message", чтобы совпадало с ViewSet
                await self.channel_layer.group_send(
                    f"chat_{chat_id}",
                    {
                        "type": "chat_message", 
                        "message": serializer_data 
                    }
                )

                # Kafka logic
                try:
                    await asyncio.wait_for(
                        send_notification_to_kafka(
                            user_id=self.user.id, 
                            message_text=text or "Media content", 
                            sender_name=self.user.username
                        ),
                        timeout=2.0
                    )
                except Exception as e:
                    print(f"KAFKA ERROR: {e}")

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")

    async def handle_typing(self, is_typing):
        if hasattr(self, 'chat_group_name'):
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "user_typing_broadcast",
                    "username": self.user.username,
                    "is_typing": is_typing
                }
            )

    async def handle_mark_read(self, chat_id):
        await self.mark_messages_as_read(chat_id)
        r.set(f"unread_count:{self.user.id}", 0)
        
        if hasattr(self, 'chat_group_name'):
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "read_event_broadcast",
                    "chat_id": chat_id,
                    "reader_id": self.user.id
                }
            )

    # --- HANDLERS (FIXED) ---

    async def chat_message(self, event):
        # FIX: Этот метод теперь универсален для HTTP POST и WebSocket
        # Мы просто берем данные из 'message' и пересылаем их клиенту
        data_to_send = event.get('message', event.get('message_data'))
        
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': data_to_send
        }))

    async def user_typing_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_update',
            'username': event['username'],
            'is_typing': event['is_typing']
        }))

    async def read_event_broadcast(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'chat_id': event['chat_id'],
            'reader_id': event['reader_id']
        }))
        
    async def unread_badge_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "unread_badge_update",
            "unread_count": event["unread_count"]
        }))

    # --- DB OPS ---

    @database_sync_to_async
    def save_message_to_db(self, chat_id, text):
        try:
            msg = Message.objects.create(chat_id=chat_id, sender=self.user, text=text)
            serializer = MessageSerializer(msg, context={'request': None})
            return msg, serializer.data
        except Exception as e:
            print(f"DB Save Error: {e}")
            return None, None

    @database_sync_to_async
    def is_chat_member(self, chat_id):
        return ChatMember.objects.filter(chat_id=chat_id, user=self.user).exists()

    @database_sync_to_async
    def get_chat_history(self, chat_id):
        messages = Message.objects.filter(chat_id=chat_id).select_related('sender').order_by('-created_at')[:50]
        return MessageSerializer(list(reversed(messages)), many=True, context={'request': None}).data
    
    @database_sync_to_async
    def mark_messages_as_read(self, chat_id):
        Message.objects.filter(chat_id=chat_id, is_read=False).exclude(sender=self.user).update(is_read=True)