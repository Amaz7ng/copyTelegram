# Этап сборки
FROM golang:1.23-alpine AS builder

RUN apk add --no-cache git

WORKDIR /app

# Копируем mod
COPY go.mod ./

# 1. Сначала скачиваем зависимости принудительно
RUN go mod download
# 2. Потом подчищаем и генерируем суммы
RUN go mod tidy

# Теперь копируем остальное (main.go и т.д.)
COPY . .

# Собираем с флагом -mod=readonly (чтобы он не пытался менять файлы во время компиляции)
RUN go build -mod=mod -o worker main.go

# Финальный образ
FROM alpine:latest
RUN apk add --no-cache ca-certificates
WORKDIR /root/
COPY --from=builder /app/worker .

CMD ["./worker"]