import json
import logging
from aiokafka import AIOKafkaProducer
import environ

env = environ.Env()
logger = logging.getLogger(__name__)

async def send_notification_to_kafka(user_id, message_text, sender_name):
    kafka_url = env('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')
    
    # Инициализируем продюсер
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_url,
        request_timeout_ms=1500,  # Не ждем долго
        retry_backoff_ms=500
    )
    
    try:
        await producer.start()
        data = {
            "user_id": int(user_id),
            "message": str(message_text),
            "sender": str(sender_name),
        }
        payload = json.dumps(data).encode('utf-8')
        
        # Отправляем без ожидания wait, чтобы максимально быстро освободить поток
        await producer.send_and_wait("notifications", payload)
        print(f"KAFKA: Sent notification for user {user_id}")
        
    except Exception as e:
        # Критично: ошибка Кафки не должна прерывать работу чата
        print(f"KAFKA ERROR: {e}")
    finally:
        await producer.stop()