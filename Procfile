release: python manage.py migrate --noinput

web: gunicorn domino.wsgi --workers $WEB_CONCURRENCY --threads 4 --worker-class=gthread --timeout 25 --keep-alive 5 --max-requests 500 --max-requests-jitter 50 --bind 0.0.0.0:$PORT

worker: celery -A domino worker --beat -l info --concurrency=2 --max-tasks-per-child=50 --prefetch-multiplier 1