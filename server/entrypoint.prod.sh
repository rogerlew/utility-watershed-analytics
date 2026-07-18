#!/bin/sh

echo "=== PRODUCTION STARTUP ==="

# Migrations are an explicit, separately credentialed deployment step.
echo "Checking migration state"
python manage.py migrate --check --noinput

# Health check
echo "Running health checks..."
python manage.py check --deploy

echo "=== PRODUCTION STARTUP COMPLETE ==="
echo "Starting Gunicorn server..."
exec "$@"
