from django.core.management.base import BaseCommand
from chats.kafka_consumer import start_kafka_consumer

class Command(BaseCommand):
    help = 'Запускает прослушивание топиков Kafka и отправку в сокеты'

    def handle(self, *args, **options):
        self.stdout.write("Запуск Kafka Consumer...")
        start_kafka_consumer()