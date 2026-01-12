import pytest
from rest_framework import status
from chats.models import Chat, ChatMember, User

@pytest.mark.django_db
class TestMessagePermissions:
    def test_member_can_send_message(self, api_client):
        """Проверка: участник чата может отправить сообщение"""
        user = User.objects.create(id=1, username="member_user")
        chat = Chat.objects.create(type=Chat.GROUP, title="Test Group")
        ChatMember.objects.create(chat=chat, user=user)

        api_client.force_authenticate(user=user)

        data = {"chat": chat.id, "text": "Hello world!"}
        response = api_client.post('/api/messages/', data)

        assert response.status_code == status.HTTP_201_CREATED

    def test_non_member_cannot_send_message(self, api_client):
        """Проверка: посторонний НЕ может отправить сообщение"""
        user = User.objects.create(id=2, username="stranger")
        chat = Chat.objects.create(type=Chat.GROUP, title="Private Group")

        api_client.force_authenticate(user=user)

        data = {"chat": chat.id, "text": "I want in!"}
        response = api_client.post('/api/messages/', data)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error'] == "Вы не участник этого чата"
        
    def test_channel_creator_can_post(self, api_client):
        """Создатель канала может публиковать посты"""
        user = User.objects.create(id=10, username="channel_creator", search_handle="boss_tag" )
        chat = Chat.objects.create(type=Chat.CHANNEL, title="News", creator=user)
        
        api_client.force_authenticate(user=user)
        
        data = {"chat": chat.id, "text": "Важная новость!"}
        response = api_client.post('/api/messages/', data)
        
        assert response.status_code == status.HTTP_201_CREATED

    def test_channel_admin_can_post(self, api_client):
        """Админ канала может публиковать посты"""
        creator = User.objects.create(id=11, username="admin_boss", search_handle="boss_tag")
        admin_user = User.objects.create(id=12, username="channel_admin", search_handle="admin_tag")
        chat = Chat.objects.create(type=Chat.CHANNEL, title="News", creator=creator)
        
        ChatMember.objects.create(chat=chat, user=admin_user, role=ChatMember.ADMIN)
        
        api_client.force_authenticate(user=admin_user)
        
        data = {"chat": chat.id, "text": "Админский пост"}
        response = api_client.post('/api/messages/', data)
        
        assert response.status_code == status.HTTP_201_CREATED

    def test_channel_member_cannot_post(self, api_client):
        """Обычный участник канала НЕ может в него писать"""
        creator = User.objects.create(id=13, username="owner", search_handle="owner_tag")
        member_user = User.objects.create(id=14, username="subscriber", search_handle="sub_tag")
        chat = Chat.objects.create(type=Chat.CHANNEL, title="News", creator=creator, )
        
        ChatMember.objects.create(chat=chat, user=member_user, role=ChatMember.MEMBER)
        
        api_client.force_authenticate(user=member_user)
        
        data = {"chat": chat.id, "text": "Я просто хотел спросить..."}
        response = api_client.post('/api/messages/', data)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['error'] == "Только админы могут писать в канал"