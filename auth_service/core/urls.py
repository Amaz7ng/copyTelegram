from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from rest_framework_simplejwt.views import TokenRefreshView

from users.views import CustomTokenObtainPairView, VerifyOTPView, RegisterView


urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('api/register/', RegisterView.as_view(), name='auth_register'),
    
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair' ),
    
    path('api/token/verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh' ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)