import secrets
import logging
from datetime import timedelta 

from .models import User

from django.utils import timezone
from django.contrib.auth.hashers import make_password

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger('users') 


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        
        if self.user.is_2fa_enabled:
            otp = ''.join(secrets.choice('0123456789') for _ in range(6))
            
            self.user.otp_code = otp
            self.user.otp_created_at = timezone.now()
            self.user.save()

            logger.info(f"Generated 2FA code for user {self.user.username}: {otp}")
            # print(f"\n[2FA] КОД ДЛЯ ПОЛЬЗОВАТЕЛЯ {self.user.username}: {otp}\n")

            return {
                "message": "OTP_SENT",
                "username": self.user.username
            }
        
        return data
    
class VerifyOTPSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        username = attrs.get('username')
        otp_code = attrs.get('otp_code')

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise serializers.ValidationError("Пользователь не найден")
        
        if not user.otp_created_at:
            raise serializers.ValidationError("Код не был сгенерирован")
        
        if timezone.now() > user.otp_created_at + timedelta(minutes=5):
            logger.warning(f"OTP expired for user {user.username}")
            user.otp_code = None
            user.save()
            raise serializers.ValidationError("Срок действия кода истек.Запросите новый.")

        if user.otp_code != otp_code:
            raise serializers.ValidationError("Неверный код подтверждения")

        refresh = RefreshToken.for_user(user)
        
        user.otp_code = None
        user.save()

        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
        
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'password', 'email', 'is_2fa_enabled')

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)