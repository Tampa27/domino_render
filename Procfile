release: python manage.py migrate --noinput

web: gunicorn domino.wsgi --workers $WEB_CONCURRENCY --threads 4 --worker-class=gthread --timeout 30 --max-requests 1000 --max-requests-jitter 100 --bind 0.0.0.0:$PORT

worker: celery -A domino worker --beat -l info --concurrency=2 --max-tasks-per-child=100 --loglevel=info