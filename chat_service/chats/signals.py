from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings
import requests
from .models import Message

@receiver(post_delete, sender=Message)
def delete_message_file(sender, instance, **kwargs):
    if instance.file:
        file_name = instance.file
        base_url = settings.MEDIA_SERVICE_URL.replace('/upload', '')
        delete_url = f"{base_url}/delete/{file_name}"
        
        try:
            requests.delete(delete_url, timeout=5)
            print(f"Сигнал: Запрос на удаление файла {file_name} отправлен.")
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при удалении файла: {e}")