from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class LoginTests(APITestCase):
    def test_login_success(self):
        User.objects.create_user(username="testuser", password="StrongPassword123!")
        url = reverse('token_obtain_pair')
        data = {
            "username": "testuser",
            "password": "StrongPassword123!"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.data)