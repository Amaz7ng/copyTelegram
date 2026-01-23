import os
import boto3
import uuid
import asyncio
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from botocore.client import Config
from dotenv import load_dotenv

from kafka_utils import producer, send_media_task

load_dotenv()

raw_endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
clean_endpoint = re.sub(r'[^a-zA-Z0-9\.\:/]', '', raw_endpoint)
if not clean_endpoint.startswith('http'):
    final_endpoint = f"http://{clean_endpoint}"
else:
    final_endpoint = clean_endpoint

print(f"DEBUG: Настройка S3 клиента на: {final_endpoint}")


s3 = boto3.client(
    's3',
    endpoint_url=final_endpoint,
    aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('MINIO_SECRET_KEY'),
    region_name='us-east-1',
    config=Config(
        signature_version='s3v4',
        s3={'addressing_style': 'path'}
    )
)

BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME', 'user-media')

def sync_prepare_minio():
    """Синхронная функция для проверки бакетов, которую мы пустим в потоке"""
    required_buckets = [BUCKET_NAME, "thumbnails"]
    for bucket in required_buckets:
        try:
            s3.head_bucket(Bucket=bucket)
            print(f"MINIO: Бакет '{bucket}' готов.")
        except Exception:
            try:
                s3.create_bucket(Bucket=bucket)
                print(f"MINIO: Бакет '{bucket}' создан успешно.")
            except Exception as e:
                print(f"MINIO ERROR: Не удалось подготовить бакет {bucket}: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("STARTUP: Запуск Kafka Producer...")
    await producer.start()
    print("STARTUP: Проверка бакетов MinIO в фоновом потоке...")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, sync_prepare_minio)
    
    print("STARTUP: Сервер готов к работе.")
    yield
    
    print("SHUTDOWN: Остановка Kafka Producer...")
    await producer.stop()

app = FastAPI(title="Media Service", lifespan=lifespan)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
        safe_name = f"{uuid.uuid4()}.{ext}"
        
        print(f"UPLOAD: Начинаю загрузку файла {file.filename} как {safe_name}")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, 
            lambda: s3.upload_fileobj(
                file.file, 
                BUCKET_NAME, 
                safe_name,
                ExtraArgs={'ContentType': file.content_type}
            )
        )

        print(f"KAFKA: Отправка задачи на обработку {safe_name}")
        await send_media_task(action="resize", filename=safe_name, bucket=BUCKET_NAME)

        return {
            "message": "Успешно загружено", 
            "original_name": file.filename,
            "saved_as": safe_name
        }
        
    except Exception as e:
        print(f"UPLOAD ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке: {str(e)}")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "media_service"}