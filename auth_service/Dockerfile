FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Ставим gunicorn для продакшн-режима
RUN pip install gunicorn 

COPY . .

# Собираем статику сразу при сборке образа
RUN python manage.py collectstatic --noinput

# Используем 8000 порт для Auth
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "core.wsgi:application"]