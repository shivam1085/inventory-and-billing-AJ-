#!/usr/bin/env bash
set -euo pipefail

# Run migrations against configured DATABASE_URL (or fallback in settings)
python manage.py migrate --no-input

# Start Gunicorn
exec gunicorn autoparts.wsgi:application
