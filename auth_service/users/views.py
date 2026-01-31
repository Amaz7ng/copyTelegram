from django.db.models import Q # Для поиска по нескольким полям
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    UserSearchSerializer, 
    CustomTokenObtainPairSerializer, 
    VerifyOTPSerializer, 
    RegisterSerializer
)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
class VerifyOTPView(APIView):
    permission_classes = [AllowAny] # Чтобы можно было подтвердить OTP без токена

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
class UserSearchView(generics.ListAPIView):
    serializer_class = UserSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('search', None)
        if query:
            # Ищем и по обычному имени, и по @хэндлу
            return User.objects.filter(
                Q(username__icontains=query) | Q(search_handle__icontains=query)
            ).distinct()[:10] # Ограничим выдачу, чтобы не грузить базу
        return User.objects.none()