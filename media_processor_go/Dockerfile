FROM golang:1.21-alpine
WORKDIR /app
COPY go.mod ./
COPY . .
RUN go build -o worker main.go
CMD ["./worker"]