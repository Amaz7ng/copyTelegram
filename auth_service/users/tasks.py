from core.celery import app
from .producer import publish_user_created_sync

@app.task(bind=True, max_retries=5)
def task_publish_user_to_kafka(self, data):
    try:
        publish_user_created_sync(data)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)