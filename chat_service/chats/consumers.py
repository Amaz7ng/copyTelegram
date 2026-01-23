import json
import asyncio
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, Chat, ChatMember
from utils.kafka_producer import send_notification_to_kafka

r = redis.Redis(host='auth_redis', port=6379, db=0, decode_responses=True)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.user_group_name = f"user_{self.user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        
        await self.accept()
        
        current_unread = r.get(f"unread_count:{self.user.id}") or 0
        await self.send(text_data=json.dumps({
            'type': 'unread_badge',
            'unread_count': int(current_unread)
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
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
            
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            
    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')

        if action == 'join_chat':
            chat_id = data.get('chat_id')
            offset = data.get('offset', 0)
            
            if await self.is_chat_member(chat_id):
                self.chat_group_name = f"chat_{chat_id}"
                
                await self.channel_layer.group_add(self.chat_group_name, self.channel_name)
                
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        "type": "user_status",
                        "user_id": self.user.id,
                        "username": self.user.username,
                        "status": "online"
                    }
                )
                
                history = await self.get_chat_history(chat_id, offset)
                
                await self.send(text_data=json.dumps({
                    'type': 'chat_history',
                    'messages': history,
                    'offset': offset,
                    'next_offset': offset + len(history)
                }))
                
                print(f"Пользователь {self.user.username} вошел в чат {chat_id}. Загружено: {len(history)}")
                
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Доступ запрещен. Вы не являетесь участником этого чата.'
                }))

        elif action == 'send_message':
            chat_id = data.get('chat_id')
            message_text = data.get('message')
            reply_to_id = data.get('reply_to_id')

            if await self.is_chat_member(chat_id):
                new_msg = await self.save_message_to_db(chat_id, message_text,reply_to_id)                
                if new_msg:
                    await self.channel_layer.group_send(
                        f"chat_{chat_id}",
                        {
                            "type": "chat_message",
                            "message": message_text,
                            "sender_username": self.user.username,
                            "sender_id": self.user.id,
                            "message_id": new_msg.id,
                            "reply_to": reply_to_id
                        }
                    )

                    recipient_ids = await self.get_all_recipients_ids(chat_id)
                    for r_id in recipient_ids:
                        asyncio.create_task(send_notification_to_kafka(
                            user_id=r_id,
                            message_text=message_text,
                            sender_name=self.user.username
                        ))
                        
                        
        elif action == 'mark_read':
            chat_id = data.get('chat_id')
            await self.mark_messages_as_read(chat_id)
            
            r.set(f"unread_count:{self.user.id}", 0)
            
            await self.send(text_data=json.dumps({
                'type': 'unread_badge',
                'unread_count': 0
            }))
            
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "messages_read_event",
                    "chat_id": chat_id,
                    "reader_id": self.user.id
                }
            )
            
        elif action == 'typing':
            await self.channel_layer.group_send(
                self.chat_group_name,
                {
                    "type": "user_typing",
                    "username": self.user.username,
                    "is_typing": data.get('is_typing')
                }
            )
            
        elif action == 'delete_message':
            message_id = data.get('message_id')
            success = await self.delete_message_from_db(message_id)
            
            if success:
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        "type": "message_delete_event",
                        "message_id": message_id
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Не удалось удалить сообщение (возможно, оно не ваше).'
                }))
                
        elif action == 'edit_message':
            message_id = data.get('message_id')
            new_text = data.get('message')
            
            success = await self.edit_message_in_db(message_id, new_text)
            
            if success:
                await self.channel_layer.group_send(
                    self.chat_group_name,
                    {
                        "type": "message_edit_event",
                        "message_id": message_id,
                        "new_text": new_text
                    }
                )
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Ошибка редактирования (сообщение не найдено или вы не автор).'
                }))

    @database_sync_to_async
    def is_chat_member(self, chat_id):
        return ChatMember.objects.filter(chat=chat_id, user=self.user).exists()      
    
    @database_sync_to_async
    def get_chat_history(self, chat_id, offset=0):
        limit = 50
        messages = Message.objects.filter(chat_id=chat_id).order_by('-created_at')[offset : offset + limit]
        
        return [{
            'id': msg.id,
            'text': msg.text,
            'sender_username': msg.sender.username,
            'sender_id': msg.sender.id,
            'created_at': msg.created_at.isoformat(),
            'is_read': msg.is_read,
        } for msg in reversed(messages)]
        
    
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
            
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_message',
            'message': event['message'],
            'sender_username': event['sender_username'],
            'sender_id': event['sender_id']
        }))

    async def send_notification(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': message
        }))
        
    @database_sync_to_async
    def save_message_to_db(self, chat_id, text, reply_to_id=None):
        try:
            chat = Chat.objects.get(id=chat_id)
            return Message.objects.create(
                chat=chat,
                sender=self.user,
                text=text,
                reply_to_id=reply_to_id
            )
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            return None
        
    @database_sync_to_async
    def mark_messages_as_read(self, chat_id):
        Message.objects.filter(
            chat_id=chat_id, 
            is_read=False
        ).exclude(sender=self.user).update(is_read=True)

    async def messages_read_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'messages_read',
            'chat_id': event['chat_id'],
            'reader_id': event['reader_id']
        }))
        
    @database_sync_to_async
    def delete_message_from_db(self, message_id):
        try:
            message = Message.objects.get(id=message_id, sender=self.user)
            message.delete()
            return True
        except Message.DoesNotExist:
            return False
        
    async def message_delete_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'delete_message',
            'message_id': event['message_id']
        }))
        
    @database_sync_to_async
    def edit_message_in_db(self, message_id, new_text):
        try:
            message = Message.objects.get(id=message_id, sender=self.user)
            message.text = new_text
            message.is_edited = True
            message.save()
            return True
        except Message.DoesNotExist:
            return False
        
    async def message_edit_event(self, event):
        await self.send(text_data=json.dumps({
            'type': 'edit_message',
            'message_id': event['message_id'],
            'new_text': event['new_text']
        }))
        
    @database_sync_to_async
    def get_all_recipients_ids(self, chat_id):
        return list(ChatMember.objects.filter(chat_id=chat_id)
                    .exclude(user=self.user)
                    .values_list('user_id', flat=True))
        
    async def unread_badge_update(self, event):
        unread_count = event['unread_count']

        await self.send(text_data=json.dumps({
            'type': 'unread_badge',
            'unread_count': unread_count
        }))