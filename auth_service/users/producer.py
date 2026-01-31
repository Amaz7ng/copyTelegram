import json
import logging
import socket
import sys
from confluent_kafka import Producer
from django.conf import settings  # Импортируем настройки Django

logger = logging.getLogger('users')

_producer = None

def delivery_report(err, msg):
    if err is not None:
        logger.error(f"[Kafka] Ошибка доставки: {err}")
    else:
        logger.info(f"[Kafka] Доставлено в топик {msg.topic()}")

def get_kafka_producer():
    """Ленивая инициализация продюсера с использованием Django Settings"""
    global _producer
    
    if 'pytest' in sys.modules or 'test' in sys.argv:
        return None

    if _producer is None:
        try:
            # Берем список серверов из настроек, которые мы прописали в settings.py
            bootstrap_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
            
            conf = {
                'bootstrap.servers': bootstrap_servers,
                'client.id': socket.gethostname(),
                'api.version.request': True,
                'broker.address.family': 'v4',
                'socket.timeout.ms': 2000,
            }
            _producer = Producer(conf)
            logger.info(f"[Kafka] Продюсер инициализирован на {bootstrap_servers}")
        except Exception as e:
            logger.error(f"[Kafka] Не удалось инициализировать продюсер: {e}")
            return None
    return _producer

def publish_user_created_sync(user_data):
    """Синхронная отправка сообщения в Kafka"""
    
    p = get_kafka_producer()
    
    if p is None:
        logger.error("[Kafka] Отправка невозможна: продюсер не создан")
        return

    try:
        # Убедимся, что тип сообщения на месте
        if 'type' not in user_data:
            user_data['type'] = 'user_created'

        p.produce(
            'user_created',
            key=str(user_data.get('id')),
            value=json.dumps(user_data).encode('utf-8'),
            callback=delivery_report
        )
        # Ждем завершения отправки (1 секунда)
        p.flush(1)
    except Exception as e:
        logger.error(f"[Kafka] Ошибка при отправке сообщения: {e}")
        raise e  # ОБЯЗАТЕЛЬНО: чтобы Celery поймал ошибку и ушел в retry