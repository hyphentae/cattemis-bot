# --- build ---
FROM golang:1.26-alpine AS builder
WORKDIR /app
COPY *.go ./
RUN go mod init webserver && go test ./... && go build -o webserver .

# --- run (scratch = ~0MB overhead) ---
FROM scratch
COPY --from=builder /app/webserver /webserver
EXPOSE 8080
ENTRYPOINT ["/webserver"]
