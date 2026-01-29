import os
from pathlib import Path
from datetime import timedelta
import environ

# Инициализация переменных окружения
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, 'django-insecure-default-key')
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

# Разрешаем все хосты, так как Nginx фильтрует трафик, а localtunnel меняет домены
ALLOWED_HOSTS = ['*']

# --- ПРИЛОЖЕНИЯ ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Сторонние
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'django_filters',

    # Мои приложения
    'users',
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', # Должен быть в самом верху
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Для статики в Docker
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

WSGI_APPLICATION = 'core.wsgi.application'

# --- БАЗА ДАННЫХ ---
DATABASES = {
    'default': env.db(), # Читает DATABASE_URL из .env
}

# --- КЭШ И СЕССИИ (REDIS) ---
CACHES = {
    'default': env.cache('REDIS_URL', default='redis://redis:6379/0')
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# --- ВАЛИДАЦИЯ ПАРОЛЕЙ ---
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

# --- REST FRAMEWORK & JWT ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# --- ЛОКАЛИЗАЦИЯ ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- СТАТИКА И МЕДИА ---
STATIC_URL = '/static/' # Важно: /static/ (со слешем)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Настройка WhiteNoise для раздачи статики
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# --- ПОЛЬЗОВАТЕЛЬ ---
AUTH_USER_MODEL = 'users.User'

# --- KAFKA ---
# Внутри Docker сети порт обычно 9092, а 9093 для внешних подключений
KAFKA_BOOTSTRAP_SERVERS = env('KAFKA_BOOTSTRAP_SERVERS', default='kafka:9092')

# --- CELERY ---
CELERY_BROKER_URL = env('REDIS_URL', default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# --- БЕЗОПАСНОСТЬ И ПРОКСИ (Ключевые настройки для Nginx + Localtunnel) ---

# CORS
CORS_ALLOW_ALL_ORIGINS = True # Разрешаем всем для удобства разработки
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins (Обязательно для HTTPS через туннель)
CSRF_TRUSTED_ORIGINS = [
    "https://*.loca.lt",
    "http://localhost",
    "http://127.0.0.1",
]

# Proxy Headers (Чтобы Django понимал, что он за SSL прокси)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True

# --- ЛОГИРОВАНИЕ ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}