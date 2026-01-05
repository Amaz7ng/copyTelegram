from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    bio = models.TextField(max_length=100, blank=True, verbose_name="о себе")
    phone_number = models.CharField(max_length=15, unique=True, null=True, blank=True, verbose_name="Номер телефона")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Аватар")
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.username