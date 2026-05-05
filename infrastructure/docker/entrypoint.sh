#!/bin/bash
# Entrypoint script for APIM application

set -e

echo "Starting APIM entrypoint..."

# Run database migrations
echo "Running database migrations..."
cd /app
alembic -c migrations/alembic/alembic.ini upgrade head

# Check if we should seed the database
if [ "$SEED_DB" = "true" ]; then
    echo "Seeding database..."
    python -m app.scripts.seed_db
fi

echo "Entrypoint tasks completed. Starting application..."

# Execute the command passed to docker run
exec "$@"
