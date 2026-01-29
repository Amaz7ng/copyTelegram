# chats/routing.py
from django.urls import re_path, path
from . import consumers

websocket_urlpatterns = [
    # Добавляем поддержку простого /ws/
    path("ws/chat/<int:chat_id>/", consumers.ChatConsumer.as_asgi()),
    # Оставляем старый, если уведомления нужны отдельно
    re_path(r'ws/notifications/$', consumers.ChatConsumer.as_asgi()),
]