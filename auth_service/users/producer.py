import json
import logging
import socket
import sys
from confluent_kafka import Producer

logger = logging.getLogger('users')

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"[Kafka] Ошибка доставки: {err}")
    else:
        logger.info(f"[Kafka] Доставлено в топик {msg.topic()}")

def publish_user_created_sync(user_data):
    
    if 'test' in sys.argv: # Если запущен pytest или manage.py test
        return
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