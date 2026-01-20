package main

import (
    "fmt"
    "time"
)

func main() {
    fmt.Println("GOPHER: Привет! Я воркер на Go, и я запущен в Docker!")
    for {
        fmt.Println("GOPHER: Ожидаю задачи из Kafka...")
        time.Sleep(10 * time.Second)
    }
}