# backend/Dockerfile
FROM python:3.11-slim

# System deps (ffmpeg required by Whisper)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

# Relax pip network timeouts (slow networks, big wheels)
ENV PIP_DEFAULT_TIMEOUT=180

WORKDIR /app

# Install Python deps (single step; uses the extra index in requirements.txt)
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# App code
COPY . /app

# Outputs directory
RUN mkdir -p /app/outputs

ENV WHISPER_MODEL=base
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
