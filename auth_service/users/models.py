import asyncio
import uuid
import random
import logging

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver

from .producer import publish_user_created

from typing import Any, Dict, Type

logger = logging.getLogger('users') 


class User(AbstractUser):
    email = models.EmailField(unique=True)
    bio = models.TextField(max_length=100, blank=True, verbose_name="о себе")
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Номер телефона")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")
    updated_at = models.DateTimeField(auto_now=True)
    
    is_2fa_enabled = models.BooleanField(default=False, verbose_name="2FA включена")
    otp_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="Код подтверждения")
    otp_created_at = models.DateTimeField(blank=True, null=True)
    
    search_handle = models.CharField(
        max_length=32, 
        unique=True, 
        db_index=True, 
        verbose_name="Тэг (username как в TG)",
        help_text="Если оставить пустым, сгенерируется автоматически"
    )
    
    def save(self, *args, **kwargs):
        if not self.search_handle:
            random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
            self.search_handle = f"user_{random_suffix}"
            
            while User.objects.filter(search_handle=self.search_handle).exists():
                random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=6))
                self.search_handle = f"user_{random_suffix}"
        
        self.search_handle = self.search_handle.lower()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username
