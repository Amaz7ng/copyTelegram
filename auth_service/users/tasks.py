from core.celery import app # Настройка селери
from .producer import publish_user_created
from asgiref.sync import async_to_sync

@app.task(bind=True, max_retries=5)
def task_publish_user_to_kafka(self, data):
    try:
        async_to_sync(publish_user_created)(data)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)