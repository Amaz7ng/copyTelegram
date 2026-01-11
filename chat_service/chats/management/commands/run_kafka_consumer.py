import json
from django.core.management.base import BaseCommand
from confluent_kafka import Consumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
from chats.models import User  

class Command(BaseCommand):
    help = 'Запуск Kafka Consumer для уведомлений'

    def handle(self, *args, **options):
        bootstrap_servers = settings.KAFKA_BOOTSTRAP_SERVERS
        
        conf = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': 'django-notifications-v3',
            'auto.offset.reset': 'earliest'
        }

        consumer = Consumer(conf)
        consumer.subscribe(['user_created'])
        
        self.stdout.write(self.style.SUCCESS(f"--- Kafka Consumer запущен на {bootstrap_servers} ---"))
        channel_layer = get_channel_layer()

        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None: continue
                if msg.error():
                    self.stdout.write(self.style.ERROR(f"Ошибка Kafka: {msg.error()}"))
                    continue

                raw_value = msg.value().decode('utf-8')
                self.stdout.write(self.style.WARNING(f"--- ПОЛУЧЕНО СООБЩЕНИЕ: {raw_value} ---"))
                
                user_data = json.loads(raw_value)
                user_id = user_data.get('id')
                username = user_data.get('username')
                search_handle = user_data.get('search_handle', f"user_{user_id}") 

                user, created = User.objects.update_or_create(
                    username=username,
                    defaults={
                        'id': user_id,
                        'search_handle': search_handle
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Пользователь {username} СОХРАНЕН в базу чатов."))

                async_to_sync(channel_layer.group_send)(
                    f"user_{user_id}",
                    {
                        "type": "send_notification",
                        "message": f"Привет, {username}! Твой профиль синхронизирован."
                    }
                )
                self.stdout.write(self.style.SUCCESS(f"Уведомление для {username} отправлено в Channel Layer"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка в цикле: {str(e)}"))
        finally:
            consumer.close()