# import json
# import logging
# import asyncio
# from confluent_kafka import Producer, Message
# import socket
# from typing import Optional, Any, Dict
# from django.conf import settings

# logger = logging.getLogger('users')

# conf = {
#     'bootstrap.servers': 'kafka:9092',
#     'client.id': socket.gethostname(),
#     'security.protocol': 'PLAINTEXT',
#     'api.version.request': True,
#     'broker.address.family': 'v4',
#     # Убираем лишние задержки
#     'queue.buffering.max.ms': 0, 
#     'request.timeout.ms': 5000,
#     'message.timeout.ms': 10000,
# }


# producer = Producer(conf)

# def delivery_report(err: Optional[Exception], msg: Message) -> None:
#     """Отчет о доставке (callback), вызывается когда Kafka подтвердила получение"""
#     if err is not None:
#         logger.error(f"[Kafka] Ошибка доставки: {err}")
#     else:
#         logger.info(f"[Kafka] Доставлено в топик {msg.topic()} [{msg.partition()}]")
        
        
# async def publish_user_created(user_data: Dict[str, Any]) -> None:
#     """Асинхронная обертка для отправки сообщения"""
#     try:
#         producer.produce(
#             'user_created',
#             key=str(user_data['id']),
#             value=json.dumps(user_data).encode('utf-8'),
#             callback=delivery_report
#         )
        
#         messages_in_queue = producer.flush(30)
        
#         if messages_in_queue > 0:
#             logger.error(f"[Kafka] Сообщение НЕ отправлено (таймаут flush)")
#         else:
#             logger.info(f"[Kafka] Сообщение успешно ушло из буфера: {user_data.get('username')}")
        
#     except Exception as e:
#         logger.error(f"[Kafka] Ошибка при отправке: {e}")
        
        
import json
import logging
import socket
from confluent_kafka import Producer

logger = logging.getLogger('users')

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"[Kafka] Ошибка доставки: {err}")
    else:
        logger.info(f"[Kafka] Доставлено в топик {msg.topic()}")

def publish_user_created_sync(user_data):
    """Синхронная отправка, идеальна для Celery"""
    conf = {
        'bootstrap.servers': 'kafka:9092',
        'client.id': socket.gethostname(),
        'api.version.request': True,
        'broker.address.family': 'v4',
        'socket.timeout.ms': 5000,
    }
    
    p = Producer(conf)
    try:
        p.produce(
            'user_created',
            key=str(user_data['id']),
            value=json.dumps(user_data).encode('utf-8'),
            callback=delivery_report
        )
        p.flush(10)
    except Exception as e:
        logger.error(f"[Kafka] Ошибка в продюсере: {e}")