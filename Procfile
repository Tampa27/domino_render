release: python manage.py migrate --noinput

# Procfile o comando de inicio
web: gunicorn domino.wsgi:application --workers=2 --threads=4 --timeout=25 --max-requests=1000

# Celery worker
worker: celery -A domino worker --beat --loglevel=info --concurrency=1 --max-tasks-per-child=100