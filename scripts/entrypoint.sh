#!/bin/sh
set -e

echo "==> [entrypoint] Waiting for database..."
python << 'PYEOF'
import os, sys, time, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cdi_project.settings')
django.setup()
from django.db import connections
from django.db.utils import OperationalError

retries = 30
for i in range(retries):
    try:
        connections['default'].ensure_connection()
        print("Database is ready!")
        break
    except OperationalError:
        print(f"Waiting for database... ({i+1}/{retries})")
        time.sleep(2)
else:
    print("ERROR: Database not available after 60s. Exiting.")
    sys.exit(1)
PYEOF

echo "==> [entrypoint] Running migrations..."
python manage.py migrate --noinput

echo "==> [entrypoint] Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> [entrypoint] Compiling locale messages..."
python manage.py compilemessages 2>/dev/null || echo "No locale files to compile, skipping."

echo "==> [entrypoint] Starting Gunicorn..."
exec gunicorn cdi_project.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
