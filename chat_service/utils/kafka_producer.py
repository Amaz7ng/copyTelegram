import environ
import json
from aiokafka import AIOKafkaProducer

env = environ.Env()

async def send_notification_to_kafka(user_id, message_text, sender_name):
    kafka_url = env('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')
    
    producer = AIOKafkaProducer(bootstrap_servers=kafka_url)
    await producer.start()
    try:
        data = {
            "user_id": user_id,
            "message": message_text,
            "sender": sender_name,
        }
        await producer.send_and_wait("notifications", json.dumps(data).encode('utf-8'))
    finally:
        await producer.stop()