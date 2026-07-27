FROM golang:1.24-bookworm AS builder
WORKDIR /src
COPY go.mod ./
COPY cmd ./cmd
COPY internal ./internal
COPY resources ./resources
RUN CGO_ENABLED=0 go test ./cmd/... ./internal/... ./resources/... && \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/cattemis-bot ./cmd/cattemis-bot

FROM python:3.12-slim-bookworm AS runtime-lite
ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl ffmpeg \
    && pip install --no-cache-dir yt-dlp \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /out/cattemis-bot /usr/local/bin/cattemis-bot
RUN useradd --create-home --uid 10001 cattemis && mkdir -p /app/data /tunnel \
    && chown -R cattemis:cattemis /app /tunnel
USER cattemis
ENTRYPOINT ["/usr/local/bin/cattemis-bot"]

FROM runtime-lite AS runtime
USER root
RUN pip install --no-cache-dir openai-whisper
USER cattemis
