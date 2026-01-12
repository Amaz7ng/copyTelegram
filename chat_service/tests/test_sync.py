import pytest
from chats.models import User
from chats.utils import save_user_from_kafka_data

@pytest.mark.django_db
class TestUserSync:
    def test_create_new_user_from_kafka(self):
        """Проверка создания нового пользователя"""
        data = {"id": 100, "username": "kafka_boy", "search_handle": "k_boy"}
        
        user, created = save_user_from_kafka_data(data)
        
        assert created is True
        assert User.objects.count() == 1
        assert user.username == "kafka_boy"

    def test_update_existing_user_from_kafka(self):
        """Проверка обновления существующего пользователя (update_or_create)"""
        User.objects.create(id=100, username="old_name", search_handle="old_handle")
        

        data = {"id": 100, "username": "new_name", "search_handle": "new_handle"}
        user, created = save_user_from_kafka_data(data)
        
        assert created is False
        assert user.username == "new_name"
        assert User.objects.get(id=100).search_handle == "new_handle"