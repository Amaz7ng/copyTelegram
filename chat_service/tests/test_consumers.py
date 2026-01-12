import pytest
from chats.models import User
from chats.utils import save_user_from_kafka_data

@pytest.mark.django_db
def test_save_user_from_kafka():
    kafka_data = {
        "id": 99,
        "username": "test_kafka_user",
        "search_handle": "user_99"
    }
    
    user, created = save_user_from_kafka_data(kafka_data)
    
    assert created is True
    assert user.id == 99
    assert user.username == "test_kafka_user"