from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

User = get_user_model()

class RegistrationTests(APITestCase):
    @patch('users.tasks.task_publish_user_to_kafka.delay')
    def test_registration(self):
        url = reverse('auth_register')
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "StrongPassword123!",
            "is_2fa_enabled": False
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="testuser").exists())
        self.assertNotIn('password', response.data)