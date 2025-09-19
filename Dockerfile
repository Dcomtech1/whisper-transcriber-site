FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pip settings
ENV PIP_DEFAULT_TIMEOUT=180
ENV PIP_ROOT_USER_ACTION=ignore
ENV PIP_NO_CACHE_DIR=1

# Install Python deps
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . /app
RUN mkdir -p /app/outputs

ENV WHISPER_MODEL=tiny
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
