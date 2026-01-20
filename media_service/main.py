import os
import boto3
from fastapi import FastAPI, UploadFile, File
from botocore.client import Config
from contextlib import asynccontextmanager
from dotenv import load_dotenv



load_dotenv()

s3 = boto3.client(
    's3',
    endpoint_url=f"http://{os.getenv('MINIO_ENDPOINT')}",
    aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('MINIO_SECRET_KEY'),
    config=Config(signature_version='s3v4')
)

BUCKET_NAME = os.getenv('MINIO_BUCKET_NAME')
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC = "media_tasks"

producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Проверка наличия бакета {BUCKET_NAME}...")
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
        print(f"Бакет {BUCKET_NAME} уже существует.")
    except Exception:
        print(f"Бакет {BUCKET_NAME} не найден. Создаю...")
        s3.create_bucket(Bucket=BUCKET_NAME)
    
    yield
    
    print("Сервис останавливается...")

app = FastAPI(title="Media Service", lifespan=lifespan)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    s3.upload_fileobj(
        file.file, 
        BUCKET_NAME, 
        file.filename,
        ExtraArgs={'ContentType': file.content_type}
    )
    
    return {"message": "Успешно загружено", "filename": file.filename}

@app.get("/health")
def health_check():
    return {"status": "ok"}