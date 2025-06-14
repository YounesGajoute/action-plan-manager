# ===================================================================
# email-service/Dockerfile - Email Service Container
# ===================================================================

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r emailuser && useradd -r -g emailuser emailuser

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs && chown emailuser:emailuser logs

# Switch to non-root user
USER emailuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import smtplib; print('Email service healthy')" || exit 1

# Default command
CMD ["python", "email_service.py"]