import json
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from confluent_kafka import Consumer, KafkaError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from chats.utils import save_user_from_kafka_data

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Запуск Kafka Consumer для синхронизации пользователей и уведомлений'

    def handle(self, *args, **options):
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'chat-service-group-v1',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
        }

        consumer = Consumer(conf)
        topic = 'user_created'
        consumer.subscribe([topic])

        self.stdout.write(self.style.SUCCESS(f"--- Kafka Consumer запущен. Слушаю топик: {topic} ---"))
        
        channel_layer = get_channel_layer()

        try:
            while True:
                msg = consumer.poll(1.0)

                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        self.stdout.write(self.style.ERROR(f"Ошибка Kafka: {msg.error()}"))
                        break

                try:
                    raw_value = msg.value().decode('utf-8')
                    user_data = json.loads(raw_value)
                    
                    self.stdout.write(self.style.WARNING(f"--- ПОЛУЧЕНО: {user_data.get('username')} ---"))
                    
                    user, created = save_user_from_kafka_data(user_data)
                    
                    status_text = "СОЗДАН" if created else "ОБНОВЛЕН"
                    self.stdout.write(self.style.SUCCESS(f"Пользователь {user.username} {status_text} в базе чатов."))

                    async_to_sync(channel_layer.group_send)(
                        f"user_{user.id}",
                        {
                            "type": "send_notification",
                            "message": f"Система: {user.username}, ваш профиль готов к работе в чатах!"
                        }
                    )
                    self.stdout.write(self.style.HTTP_INFO(f"Уведомление отправлено в Channel Layer для user_{user.id}"))

                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR(f"Ошибка декодирования JSON: {msg.value()}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Ошибка при обработке сообщения: {str(e)}"))

        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("Консьюмер остановлен вручную."))
        finally:
            consumer.close()