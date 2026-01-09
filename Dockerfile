FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libimage-exiftool-perl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install rclone
RUN curl https://rclone.org/install.sh | bash

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY main.py .

# Create data directories
RUN mkdir -p /data/watch /data/clean

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DAEMON_MODE=true
ENV WATCH_DIR=/data/watch
ENV OUTPUT_DIR=/data/clean
ENV RCLONE_REMOTE_NAME=gdrive
ENV RCLONE_DEST_PATH=backups

# Expose API port
EXPOSE 8000

# Set entrypoint
ENTRYPOINT ["python", "main.py"]
