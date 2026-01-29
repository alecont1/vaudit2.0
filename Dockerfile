# AuditEng V2 Backend Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy all source code first
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Create data directory for uploads
RUN mkdir -p /app/data/uploads

# Expose port (Railway uses PORT env var)
EXPOSE 8000

# Run the application
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
