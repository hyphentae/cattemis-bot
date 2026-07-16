FROM python:3.14-slim

# ffmpeg нужен yt-dlp для мёрджа видео+аудио
# curl нужен для установки cloudflared
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb \
       -o /tmp/cloudflared.deb \
    && dpkg -i /tmp/cloudflared.deb \
    && rm /tmp/cloudflared.deb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY cattemis_bot/ ./cattemis_bot/
COPY web/ ./web/
COPY run.py ./run.py

RUN useradd -m -u 1000 botuser
USER botuser

CMD ["python", "run.py"]
