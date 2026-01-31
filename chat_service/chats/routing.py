# chats/routing.py
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # Основной путь для чата. <int:chat_id> попадет в scope['url_route']['kwargs']
    path("ws/chat/<int:chat_id>/", consumers.ChatConsumer.as_asgi()),
    
    # Если ты хочешь сделать один общий сокет для уведомлений (вне конкретного чата)
    # можно использовать тот же консьюмер, но проверять наличие chat_id в коде
    path("ws/notifications/", consumers.ChatConsumer.as_asgi()),
]