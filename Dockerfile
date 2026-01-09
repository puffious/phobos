FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    libimage-exiftool-perl \
    && rm -rf /var/lib/apt/lists/*

# Install rclone
RUN curl https://rclone.org/install.sh | bash

# Set working directory
WORKDIR /app

# Copy application code
COPY app/ /app/app/
COPY requirements.txt /app/
COPY main.py /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create data directories
RUN mkdir -p /data/watch /data/clean /config/rclone

ENTRYPOINT ["python", "main.py"]
