# --- frontend ---
FROM node:24-alpine AS frontend
WORKDIR /frontend
COPY client/package.json client/package-lock.json ./
RUN npm ci
COPY client/ ./
RUN npm run build

# --- server build ---
FROM golang:1.26-alpine AS builder
WORKDIR /app
COPY server/*.go ./
RUN go mod init webserver && go test ./... && go build -o webserver .

# --- run (scratch = ~0MB overhead) ---
FROM scratch
COPY --from=builder /app/webserver /webserver
COPY --from=frontend /frontend/dist /static
EXPOSE 8080
ENTRYPOINT ["/webserver"]
