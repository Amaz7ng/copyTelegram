from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.conf import settings
import requests
from .models import Message

@receiver(post_delete, sender=Message)
def delete_message_file(sender, instance, **kwargs):
    if instance.file:
        # Берем только имя файла, так как в базе он может лежать как 'chat_files/abc.jpg'
        import os
        file_name = os.path.basename(instance.file.name)
        
        # Правильно чистим URL
        base_url = settings.MEDIA_SERVICE_URL.split('/upload')[0]
        delete_url = f"{base_url}/delete/{file_name}"
        
        # В идеале это должно быть задачей Celery, но для начала ок
        try:
            requests.delete(delete_url, timeout=5)
        except Exception as e:
            print(f"Ошибка удаления файла: {e}")