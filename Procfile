release: python manage.py makemigrations && python manage.py migrate

web: gunicorn domino.wsgi --workers 2 --bind 0.0.0.0:$PORT

worker: celery -A domino worker --beat -l info