import json
import redis
from django.core.management.base import BaseCommand
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from confluent_kafka import Consumer, KafkaError

r = redis.Redis(host='auth_redis', port=6379, db=0, decode_responses=True)
channel_layer = get_channel_layer()

class Command(BaseCommand):
    help = 'Слушает Kafka и обновляет счетчики в Redis'

    def handle(self, *args, **options):
        conf = {
            'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'notifications-group-v1',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
        }

        consumer = Consumer(conf)
        consumer.subscribe(['notifications'])

        self.stdout.write(self.style.SUCCESS("--- Воркер Badge-уведомлений запущен ---"))

        try:
            while True:
                msg = consumer.poll(1.0)
                if msg is None or msg.error():
                    continue

                try:
                    data = json.loads(msg.value().decode('utf-8'))
                    user_id = data.get('user_id')
                    
                    redis_key = f"unread_count:{user_id}"
                    new_count = r.incr(redis_key)
                    
                    async_to_sync(channel_layer.group_send)(
                    f"user_{user_id}", 
                    {
                        "type": "unread_badge_update",
                        "unread_count": new_count
                    }
                )
                    
                    self.stdout.write(f"User {user_id} unread count: {new_count}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))

        finally:
            consumer.close()