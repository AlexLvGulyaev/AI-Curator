FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for asyncpg, Git workflow and general build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./
COPY scripts/ ./scripts/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY pytest.ini .
COPY tests/ ./tests/

# Ensure storage directories exist
RUN mkdir -p /app/storage/documents /app/storage/cache

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
