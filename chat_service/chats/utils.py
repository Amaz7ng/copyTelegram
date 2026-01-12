from chats.models import User

def save_user_from_kafka_data(user_data):
    user_id = user_data.get('id')
    username = user_data.get('username')
    search_handle = user_data.get('search_handle', f"user_{user_id}")

    user, created = User.objects.update_or_create(
        id=user_id,
        defaults={
            'username': username,
            'search_handle': search_handle
        }
    )
    return user, created