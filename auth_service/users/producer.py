import json
import logging
import socket
import sys
from confluent_kafka import Producer

logger = logging.getLogger('users')

_producer = None

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"[Kafka] Ошибка доставки: {err}")
    else:
        logger.info(f"[Kafka] Доставлено в топик {msg.topic()}")

def get_kafka_producer():
    """Ленивая инициализация продюсера: создается только при реальном вызове"""
    global _producer
    
    if 'pytest' in sys.modules or 'test' in sys.argv:
        return None

    if _producer is None:
        try:
            conf = {
                'bootstrap.servers': 'kafka:9092',
                'client.id': socket.gethostname(),
                'api.version.request': True,
                'broker.address.family': 'v4',
                'socket.timeout.ms': 2000,
            }
            _producer = Producer(conf)
        except Exception as e:
            logger.error(f"[Kafka] Не удалось инициализировать продюсер: {e}")
            return None
    return _producer

def publish_user_created_sync(user_data):
    """Синхронная отправка сообщения в Kafka"""
    
    p = get_kafka_producer()
    
    if p is None:
        return

    try:
        p.produce(
            'user_created',
            key=str(user_data['id']),
            value=json.dumps(user_data).encode('utf-8'),
            callback=delivery_report
        )
        p.flush(1)
    except Exception as e:
        logger.error(f"[Kafka] Ошибка при отправке сообщения: {e}")