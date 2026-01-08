import json
from confluent_kafka import Consumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def start_kafka_consumer():
    conf = {
        'bootstrap.servers': 'kafka:9093',
        'group.id': 'django-notifications',
        'auto.offset.reset': 'earliest'
    }

    consumer = Consumer(conf)
    consumer.subscribe(['user_created'])

    channel_layer = get_channel_layer()

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None: continue
            if msg.error(): continue

            user_data = json.loads(msg.value().decode('utf-8'))
            user_id = user_data.get('id')

            async_to_sync(channel_layer.group_send)(
                f"user_{user_id}",
                {
                    "type": "send_notification",
                    "message": f"Привет, {user_data['username']}! Твой профиль успешно синхронизирован."
                }
            )
    finally:
        consumer.close()