import json
import asyncio
from confluent_kafka import Producer, Message
import socket
from typing import Optional, Any, Dict



conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': socket.gethostname(),
    'queue.buffering.max.ms': 5, 
}

producer = Producer(conf)

def delivery_report(err: Optional[Exception], msg: Message) -> None:
    """Отчет о доставке (callback), вызывается когда Kafka подтвердила получение"""
    if err is not None:
        print(f" [Kafka] Ошибка доставки: {err}")
    else:
        print(f" [Kafka] Доставлено в топик {msg.topic()} [{msg.partition()}]")

async def publish_user_created(user_data: Dict[str, Any]) -> None:
    """Асинхронная обертка для отправки сообщения"""
    try:
        producer.produce(
            'user_created',
            key=str(user_data['id']),
            value=json.dumps(user_data).encode('utf-8'),
            callback=delivery_report
        )
        
        producer.poll(0) 
        producer.flush(1)
        
        print(f" [Kafka] Сообщение в очереди на отправку: {user_data['username']}")
        
    except Exception as e:
        print(f" [Kafka] Ошибка: {e}")