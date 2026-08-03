#!/bin/bash
set -e

# Apply database migrations before starting the application.
echo "Applying database migrations..."
alembic upgrade head

# Start the application.
echo "Starting AI Curator backend..."
exec "$@"
