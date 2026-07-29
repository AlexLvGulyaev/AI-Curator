FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for asyncpg and general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY pytest.ini .
COPY tests/ ./tests/

# Ensure document storage directory exists
RUN mkdir -p /app/storage/documents

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
