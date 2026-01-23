FROM golang:1.24-alpine

RUN apk add --no-cache git 

WORKDIR /app

ENV GOPROXY=https://proxy.golang.org,direct

COPY *.go ./

RUN go mod init media_processor_go || true

RUN go mod tidy

RUN go build -o worker .

RUN chmod +x worker

CMD ["./worker"]