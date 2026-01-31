import json
import redis
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from confluent_kafka import Consumer, KafkaError

logger = logging.getLogger(__name__)

# Совет: вынеси настройки Redis в settings.py
REDIS_HOST = getattr(settings, 'REDIS_HOST', 'redis') 
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

class Command(BaseCommand):
    help = 'Слушает Kafka и обновляет счетчики в Redis для Badge-уведомлений'

    def handle(self, *args, **options):
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'notifications-group-v1',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
        }

        consumer = Consumer(conf)
        consumer.subscribe(['notifications'])
        channel_layer = get_channel_layer()

        self.stdout.write(self.style.SUCCESS("--- Воркер Badge-уведомлений запущен и слушает Kafka ---"))

        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    self.stdout.write(self.style.ERROR(f"Kafka error: {msg.error()}"))
                    continue

                try:
                    data = json.loads(msg.value().decode('utf-8'))
                    
                    # Поддержка и одиночного ID, и списка (для гибкости)
                    user_ids = data.get('user_ids') or [data.get('user_id')]
                    
                    for u_id in user_ids:
                        if not u_id:
                            continue
                            
                        # 1. Инкремент в Redis
                        redis_key = f"unread_count:{u_id}"
                        new_count = r.incr(redis_key)
                        
                        # 2. Отправка через WebSocket
                        # В ChatConsumer должен быть метод unread_badge_update
                        async_to_sync(channel_layer.group_send)(
                            f"user_{u_id}", 
                            {
                                "type": "unread_badge_update",
                                "unread_count": int(new_count)
                            }
                        )
                        self.stdout.write(f"Updated badge for User {u_id}: {new_count}")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Ошибка при обработке сообщения: {e}"))

        except KeyboardInterrupt:
            pass
        finally:
            consumer.close()