FROM python:3.12.8-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . .

# Apply migrations, create superuser, and start Daphne
CMD python manage.py migrate && \
    python manage.py createsuperuser --noinput --username admin --email admin@example.com && \
    python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); u = User.objects.get(username='admin'); u.set_password('adminpass@123'); u.save()" && \
    daphne -b 0.0.0.0 -p 8000 chat_application.asgi:application