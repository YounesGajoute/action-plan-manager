# ===================================================================
# Dockerfile for Action Plan Manager - Backup Service
# ===================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    wget \
    cron \
    awscli \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backup service files
COPY backup_service.py .
COPY database_backup.py .
COPY file_backup.py .
COPY s3_uploader.py .

# Create necessary directories
RUN mkdir -p /app/backups /app/logs /app/data

# Create backup user
RUN useradd -m -s /bin/bash backup && \
    chown -R backup:backup /app

# Switch to backup user
USER backup

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import backup_service; print('OK')" || exit 1

# Default command
CMD ["python", "backup_service.py"]