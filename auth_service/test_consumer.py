from confluent_kafka import Consumer, KafkaError
import json

c = Consumer({
    'bootstrap.servers': 'kafka:9093',
    'group.id': 'my-test-group',
    'auto.offset.reset': 'earliest'
})

c.subscribe(['user_created'])

print("Слушаю Kafka... Создай пользователя в админке!")

try:
    while True:
        msg = c.poll(1.0)
        if msg is None: continue
        if msg.error():
            print(f"Ошибка: {msg.error()}")
        else:
            data = json.loads(msg.value().decode('utf-8'))
            print(f"Успех! Получены данные из Kafka: {data}")
finally:
    c.close()