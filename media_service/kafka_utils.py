import os
import json
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = "media_tasks"

producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

async def send_media_task(action: str, filename: str, bucket: str):
    """Удобная функция-обертка для отправки задач"""
    message = {
        "action": action,
        "filename": filename,
        "bucket": bucket
    }
    payload = json.dumps(message).encode('utf-8')
    await producer.send_and_wait(KAFKA_TOPIC, payload)