import pytest
from rest_framework import status
from chats.models import Chat, ChatMember, User

@pytest.mark.django_db
class TestDirectMessages:
    def test_create_direct_chat_on_first_message(self, api_client):
        """Проверка: чат создается автоматически при первой отправке сообщения"""
        sender = User.objects.create(id=20, username="sender", search_handle="s_tag")
        receiver = User.objects.create(id=21, username="receiver", search_handle="r_tag")
        
        api_client.force_authenticate(user=sender)
        
        data = {"receiver_id": receiver.id, "text": "Привет!"}
        response = api_client.post('/api/messages/', data)
        
        assert response.status_code == status.HTTP_201_CREATED
        
        chat = Chat.objects.filter(type=Chat.DIRECT).first()
        assert chat is not None
        
        members_count = ChatMember.objects.filter(chat=chat).count()
        assert members_count == 2
        assert ChatMember.objects.filter(chat=chat, user=sender).exists()
        assert ChatMember.objects.filter(chat=chat, user=receiver).exists()

    def test_reuse_existing_direct_chat(self, api_client):
        """Проверка: повторное сообщение не плодит чаты"""
        u1 = User.objects.create(id=22, username="u1", search_handle="h1")
        u2 = User.objects.create(id=23, username="u2", search_handle="h2")
        
        chat = Chat.objects.create(type=Chat.DIRECT)
        ChatMember.objects.create(chat=chat, user=u1)
        ChatMember.objects.create(chat=chat, user=u2)
        
        api_client.force_authenticate(user=u1)
        
        data = {"receiver_id": u2.id, "text": "Снова привет"}
        api_client.post('/api/messages/', data)
        
        assert Chat.objects.filter(type=Chat.DIRECT).count() == 1