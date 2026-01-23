package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"image"
	"io"
	"log"
	"os"
	"strings"

	_ "image/gif"
	_ "image/jpeg"
	"image/png"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
	"github.com/nfnt/resize"
	"github.com/segmentio/kafka-go"
)

type MediaTask struct {
	Action   string `json:"action"`
	Filename string `json:"filename"`
	Bucket   string `json:"bucket"`
}

func main() {
	endpoint := os.Getenv("MINIO_ENDPOINT")
	endpoint = strings.TrimPrefix(endpoint, "http://")
	endpoint = strings.TrimPrefix(endpoint, "https://")

	if endpoint == "" {
		endpoint = "media_storage:9000"
	}

	accessKey := os.Getenv("MINIO_ACCESS_KEY")
	secretKey := os.Getenv("MINIO_SECRET_KEY")

	minioClient, err := minio.New(endpoint, &minio.Options{
		Creds:        credentials.NewStaticV4(accessKey, secretKey, ""),
		Secure:       false,
		BucketLookup: minio.BucketLookupPath,
	})
	if err != nil {
		log.Fatalln("GOPHER: Ошибка создания клиента MinIO:", err)
	}
	buckets := []string{"media", "thumbnails", "user-media"}
	for _, bucket := range buckets {
		exists, err := minioClient.BucketExists(context.Background(), bucket)
		if err == nil && !exists {
			fmt.Printf("GOPHER: Бакет %s не найден, создаю...\n", bucket)
			_ = minioClient.MakeBucket(context.Background(), bucket, minio.MakeBucketOptions{})
		}
	}

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: []string{"kafka:9092"},
		Topic:   "media_tasks",
		GroupID: "go-worker-group-v5",
		StartOffset: kafka.FirstOffset,
	})

	fmt.Printf("GOPHER: Я запущен! Подключен к %s и слушаю Kafka...\n", endpoint)

	for {
		m, err := reader.ReadMessage(context.Background())
		if err != nil {
			log.Printf("GOPHER: Ошибка чтения Kafka: %v", err)
			continue
		}

		var task MediaTask
		if err := json.Unmarshal(m.Value, &task); err != nil {
			log.Printf("GOPHER: Ошибка парсинга JSON: %v", err)
			continue
		}

		fmt.Printf("GOPHER: Принял задачу! Файл: %s из бакета %s\n", task.Filename, task.Bucket)
		err = processImage(minioClient, task.Bucket, task.Filename)
		if err != nil {
			log.Printf("!!! ОШИБКА ОБРАБОТКИ: %v", err)
		} else {
			fmt.Printf("GOPHER: Успешно сделал миниатюру для %s\n", task.Filename)
		}
		fmt.Println("GOPHER: Готов к следующей задаче.")
	}
}

func processImage(minioClient *minio.Client, bucketName string, filename string) error {
	ctx := context.Background()

	object, err := minioClient.GetObject(ctx, bucketName, filename, minio.GetObjectOptions{})
	if err != nil {
		return fmt.Errorf("ошибка получения объекта: %v", err)
	}
	defer object.Close()

	data, err := io.ReadAll(object)
	if err != nil {
		return fmt.Errorf("read error: %v", err)
	}

	stat, err := object.Stat()
	if err != nil {
		return fmt.Errorf("ошибка Stat: %v", err)
	}
	fmt.Printf("GOPHER: Размер файла для обработки: %d байт\n", stat.Size)

	img, format, err := image.Decode(bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("decode error (format: %s): %v", format, err)
	}

	fmt.Printf("GOPHER: Успешно прочитан %s, формат: %s\n", filename, format)

	newImg := resize.Resize(200, 0, img, resize.Lanczos3)

	var buf bytes.Buffer
	if err := png.Encode(&buf, newImg); err != nil {
		return fmt.Errorf("ошибка кодирования PNG: %v", err)
	}

	thumbName := "thumb_" + filename
	_, err = minioClient.PutObject(ctx, "thumbnails", thumbName, &buf, int64(buf.Len()), minio.PutObjectOptions{
		ContentType: "image/png",
	})

	return err
}