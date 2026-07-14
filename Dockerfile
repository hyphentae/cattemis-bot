FROM python:3.12-slim

# ffmpeg нужен yt-dlp для мёрджа видео+аудио
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Зависимости отдельным слоем — пересборка только при изменении requirements
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Исходники
COPY cattemis_bot/ ./cattemis_bot/
COPY web/ ./web/
COPY run.py ./run.py

# Не запускать от root
RUN useradd -m -u 1000 botuser
USER botuser

CMD ["python", "run.py"]
