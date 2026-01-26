from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import TokenRefreshView

from users.views import CustomTokenObtainPairView, VerifyOTPView, RegisterView, UserSearchView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/auth/register/', RegisterView.as_view(), name='auth_register'),
    path('api/auth/users/', UserSearchView.as_view(), name='user_search'),
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    path('api/auth/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)