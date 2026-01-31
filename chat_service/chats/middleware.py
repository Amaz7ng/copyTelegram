import jwt
import logging
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs

User = get_user_model()
logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        # Важно: если Kafka еще не синхронизировала юзера, 
        # он не сможет подключиться к сокету, пока воркер не отработает.
        logger.warning(f"User {user_id} not found in Chat DB. Kafka lag?")
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()
        
        token = None
        query_string = scope.get("query_string", b"").decode()
        
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            try:
                # Декодируем токен
                decoded_data = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=["HS256"]
                )
                
                user_id = decoded_data.get("user_id")
                
                if user_id:
                    scope["user"] = await get_user(user_id)
                    logger.debug(f"User {user_id} authenticated via WebSocket")
                else:
                    scope["user"] = AnonymousUser()
                    
            except jwt.ExpiredSignatureError:
                logger.warning("Token expired")
                scope["user"] = AnonymousUser()
            except jwt.InvalidTokenError:
                logger.warning("Invalid token")
                scope["user"] = AnonymousUser()
            except Exception as e:
                logger.error(f"JWT Unknown Error: {e}")
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)