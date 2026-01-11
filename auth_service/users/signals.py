from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from .tasks import task_publish_user_to_kafka 

@receiver(post_save, sender=User)
def user_created_sig(sender, instance, created, **kwargs):
    if created:
        data = {
            'id': instance.id,
            'username': instance.username,
            'search_handle': instance.search_handle,
            'email': instance.email,
            'avatar': instance.avatar.url if instance.avatar else None
        }
        task_publish_user_to_kafka.delay(data)