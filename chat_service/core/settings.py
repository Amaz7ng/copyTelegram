import os
from pathlib import Path
import environ

# Инициализация переменных окружения
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'django-insecure-default-key-chat')
)

# Определение путей
BASE_DIR = Path(__file__).resolve().parent.parent

# Чтение .env файла
env_file = os.path.join(BASE_DIR, '.env')
if not os.path.exists(env_file):
    env_file = os.path.join(BASE_DIR.parent, '.env')

if os.path.exists(env_file):
    environ.Env.read_env(env_file)

# --- ОСНОВНЫЕ НАСТРОЙКИ ---
SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

# Разрешаем все хосты (фильтрацию берет на себя Nginx и фаервол)
ALLOWED_HOSTS = ['*']

# --- ПРИЛОЖЕНИЯ ---
INSTALLED_APPS = [
    'daphne', # ВАЖНО: Должно быть первым для работы WebSocket/ASGI
    
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'rest_framework',
    'channels', # Для WebSocket
    'chats', # Твое приложение
    
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # В самом верху для обработки заголовков
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Для статики
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- СЕРВЕРНЫЕ НАСТРОЙКИ (WSGI / ASGI) ---
WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'

# --- БАЗА ДАННЫХ ---
DATABASES = {
    'default': env.db(), # Читает DATABASE_URL из .env
}

# --- CHANNELS (WebSocket) ---
# Используем Redis как брокер сообщений для чатов
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            # Используем базу 1, чтобы не мешать Celery (обычно база 0)
            "hosts": [env('REDIS_URL', default='redis://redis:6379/1')],
        },
    },
}

# --- REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication', 
        # SessionAuth можно оставить для админки, но для API лучше только JWT
        'rest_framework.authentication.SessionAuthentication',   
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ]
}

# --- ВАЛИДАЦИЯ ПАРОЛЕЙ ---
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# --- ЛОКАЛИЗАЦИЯ ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- СТАТИКА И МЕДИА ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Настройка WhiteNoise для эффективной раздачи статики в Docker
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Медиа настройки
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT, exist_ok=True)


MEDIA_SERVICE_INTERNAL_URL = "http://fastapi_media:8002/upload"
# URL для доступа к микросервису медиа (через Nginx)
MEDIA_SERVICE_URL = "/api/media/"

# --- KAFKA ---
KAFKA_BOOTSTRAP_SERVERS = env('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')

# --- ПОЛЬЗОВАТЕЛЬ ---
AUTH_USER_MODEL = 'chats.User'

# --- БЕЗОПАСНОСТЬ И ПРОКСИ (Ключевое для Localtunnel) ---

# CORS
CORS_ALLOW_ALL_ORIGINS = True # Разрешаем всем (удобно для разработки)
CORS_ALLOW_CREDENTIALS = True



# --- ДОПОЛНИТЕЛЬНО ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

from datetime import timedelta

SIMPLE_JWT = {
    'SIGNING_KEY': SECRET_KEY, # Используем тот же ключ, что и в Auth Service
    'AUTH_HEADER_TYPES': ('Bearer',),
    'ALGORITHM': 'HS256',      # Должен совпадать с Auth Service
}

FORCE_SCRIPT_NAME = None

CSRF_TRUSTED_ORIGINS = [
    "https://*.loca.lt",
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True