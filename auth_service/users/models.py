import asyncio

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

from .producer import publish_user_created

from typing import Any, Dict, Type


class User(AbstractUser):
    bio = models.TextField(max_length=100, blank=True, verbose_name="о себе")
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Номер телефона")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")
    updated_at = models.DateTimeField(auto_now=True)
    
    is_2fa_enable = models.BooleanField(default=False, verbose_name="2FA включена")
    otp_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="Код подтверждения")
    otp_created_at = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return self.username
    
@receiver(post_save, sender=User)
def user_created_sig(sender: Type[User], 
                         instance: User, 
                         created: bool, 
                         **kwargs: Dict[str, Any]) -> None:
        """
    Сигнал: срабатывает ПОСЛЕ сохранения пользователя в базу.
    """
        if created:
            data = {
				'id': instance.id,
				'username': instance.username,
				'email': instance.email
			}
            
            try:
                from asgiref.sync import async_to_sync
                async_to_sync(publish_user_created)(data)
            except Exception as e:
                print(f"Ошибка при запуске Kafka задачи: {e}")