from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class OTPTests(APITestCase):
    def test_login_with_2fa_enabled(self):
        """Проверка, что при включенном 2FA токены не выдаются сразу"""
        User.objects.create_user(
            username="2fa_user", 
            password="StrongPassword123!",
            is_2fa_enabled=True
        )
        url = reverse('token_obtain_pair')
        data = {"username": "2fa_user", "password": "StrongPassword123!"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('message'), "OTP_SENT")
        self.assertNotIn('access', response.data)

    def test_verify_otp_success(self):
        """Проверка успешного ввода OTP кода и получения токенов"""
        user = User.objects.create_user(
            username="otp_user", 
            password="password123",
            otp_code="123456",
            otp_created_at=timezone.now()
        )
        url = reverse('verify_otp')
        data = {"username": "otp_user", "otp_code": "123456"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)
        
        user.refresh_from_db() # Обновляем объект из базы, чтобы увидеть сброс кода
        self.assertIsNone(user.otp_code)