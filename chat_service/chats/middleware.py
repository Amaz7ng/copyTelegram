import jwt
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        close_old_connections()
        
        token = None
        query_string = scope.get("query_string", b"").decode()
        
        from urllib.parse import parse_qs
        query_params = parse_qs(query_string)
        token = query_params.get("token", [None])[0]

        if token:
            try:
                print(f"DEBUG: Processing token: {token[:10]}...") 
                
                decoded_data = jwt.decode(
                    token, 
                    settings.SECRET_KEY, 
                    algorithms=["HS256"]
                )
                user_id = decoded_data.get("user_id")
                
                if user_id:
                    scope["user"] = await get_user(user_id)
                    print(f"DEBUG: User {user_id} authenticated successfully!")
                else:
                    print("DEBUG: No user_id in token")
                    scope["user"] = AnonymousUser()
                    
            except Exception as e:
                print(f"DEBUG: JWT Decode Error: {str(e)}")
                scope["user"] = AnonymousUser()
        else:
            scope["user"] = AnonymousUser()

        return await self.inner(scope, receive, send)