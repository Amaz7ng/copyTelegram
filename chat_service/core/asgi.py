import os
import django
from django.core.asgi import get_asgi_application

# 1. Устанавливаем настройки
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# 2. Инициализируем Django
django.setup()

# 3. Создаем HTTP ASGI приложение сразу после setup
django_asgi_app = get_asgi_application()

# 4. Импортируем всё остальное ТОЛЬКО ПОСЛЕ django.setup()
from channels.routing import ProtocolTypeRouter, URLRouter
from chats.middleware import JWTAuthMiddleware 
from chats.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    # Обработка обычных HTTP запросов
    "http": django_asgi_app,
    
    # Обработка WebSocket соединений
    "websocket": JWTAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})