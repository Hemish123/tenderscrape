#!/bin/bash
# Azure App Service startup script
# Runs migrations and starts Gunicorn with the custom config (300s timeout)

echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Starting Gunicorn ==="
gunicorn tender_project.wsgi:application --config gunicorn.conf.py
