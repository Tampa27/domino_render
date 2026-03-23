release: python manage.py migrate --noinput

web: gunicorn domino.wsgi --workers 2 --bind 0.0.0.0:$PORT

worker: celery -A domino worker --beat -l info