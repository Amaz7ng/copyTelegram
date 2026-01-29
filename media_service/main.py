import os
import re
import uuid
import boto3
import asyncio
from dotenv import load_dotenv
from botocore.client import Config
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from kafka_utils import producer, send_media_task
from fastapi import FastAPI, UploadFile, File, HTTPException

load_dotenv()

raw_endpoint = os.getenv('MINIO_ENDPOINT', 'minio:9000')
if not raw_endpoint.startswith('http'):
    final_endpoint = f"http://{raw_endpoint}"
else:
    final_endpoint = raw_endpoint

print(f"DEBUG: Connecting to MinIO at: {final_endpoint}")

s3 = boto3.client(
    's3',
    endpoint_url=final_endpoint,
    aws_access_key_id=os.getenv('MINIO_ACCESS_KEY', 'media_admin'),
    aws_secret_access_key=os.getenv('MINIO_SECRET_KEY', 'media_password'),
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
    
@app.delete("/delete/{file_name}")
async def delete_file(file_name: str):
    try:
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            None, 
            lambda: s3.delete_object(Bucket=BUCKET_NAME, Key=file_name)
        )
        print(f"DELETE: Оригинал {file_name} удален из {BUCKET_NAME}")
        thumb_name = f"thumb_{file_name}"
        await loop.run_in_executor(
            None, 
            lambda: s3.delete_object(Bucket="thumbnails", Key=thumb_name)
        )
        print(f"DELETE: Миниатюра {thumb_name} удалена из thumbnails")

        return {"status": "success", "message": f"Файлы {file_name} удалены"}
        
    except Exception as e:
        print(f"DELETE ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении: {str(e)}")
    
@app.get("/media/{file_name}")
async def get_file(file_name: str):
    try:
        # Пытаемся забрать файл из бакета
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: s3.get_object(Bucket=BUCKET_NAME, Key=file_name)
        )
        # Отдаем поток байтов напрямую в браузер
        return StreamingResponse(
            response['Body'], 
            media_type=response.get('ContentType', 'image/jpeg')
        )
    except Exception as e:
        print(f"GET ERROR: {str(e)}")
        raise HTTPException(status_code=404, detail="Файл не найден в хранилище")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "media_service"}