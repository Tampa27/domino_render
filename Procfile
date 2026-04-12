release: python manage.py migrate --noinput

# Web con PgBouncer (cambia daphne por bin/start-pgbouncer)
web: bin/start-pgbouncer daphne -b 0.0.0.0 -p $PORT domino.asgi:application

# Celery worker
worker: celery -A domino worker --beat --loglevel=info --concurrency=1 --max-tasks-per-child=100