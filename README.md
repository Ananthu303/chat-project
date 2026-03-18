# Chat Application (Django + Channels)

Real-time chat app built with **Django**, **Channels (WebSockets)**, and **Daphne**.

## Features

- **Email-based auth** with custom user model
- **Register / Login / Logout**
- **User list** with online/offline status updates (WebSockets)
- **1:1 chat** with:
  - real-time messaging (WebSockets)
  - message history (stored in DB)
  - read receipts
  - delete (sender-only)

## Tech stack

- **Python**: 3.12 (Docker image uses `python:3.12.8-slim`)
- **Django**: 6.x
- **Channels**: 4.x
- **Daphne**: ASGI server
- **Database**: SQLite (`db.sqlite3`) by default
- **Static files**: WhiteNoise

## Project structure (high level)

- `chat_application/`: Django project (settings/urls/asgi)
- `chat/`: chat app (models, views, websocket consumers)
- `manage.py`: Django entrypoint
- `requirements.txt`: Python dependencies
- `Dockerfile`, `docker-compose.yml`: container setup

## Prerequisites

- **Python 3.12+**
- (Optional) **Docker + Docker Compose**

## Local setup (Windows / macOS / Linux)

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

Start the app (ASGI via Daphne):

```bash
daphne -b 127.0.0.1 -p 8000 chat_application.asgi:application
```

Open the app:

- **Web UI**: `http://127.0.0.1:8000/`
- **Admin**: `http://127.0.0.1:8000/admin/` (create an admin user with `python manage.py createsuperuser`)

## Routes

- **Register**: `/`
- **Login**: `/login/`
- **Logout**: `/logout/`
- **Users list**: `/users/`
- **Chat**: `/chat/<uid>/`

## WebSocket endpoints

The app uses Channels WebSockets (served by the same Daphne process):

- **User status / user list**: `/ws/users/`
- **Chat**: `/ws/chat/<uid>/`

## Docker (recommended quick start)

Build and run:

```bash
docker compose up --build
```

Then open:

- `http://127.0.0.1:8000/`

Create an admin user (first time only):

```bash
docker compose exec web python manage.py createsuperuser
```

### Notes about Redis

`docker-compose.yml` starts a Redis container, but the current Django settings use the **in-memory** channel layer:

- `chat_application/settings.py` sets `CHANNEL_LAYERS` to `channels.layers.InMemoryChannelLayer`

That means Redis is **not required** for local/dev as currently configured. If you want to use Redis (recommended for production / multi-worker), update `CHANNEL_LAYERS` to use `channels_redis` and point it at the `redis` service.

## Common commands

```bash
# Create migrations (if you change models)
docker compose exec web python manage.py makemigrations

# Apply migrations (Optional - Migrations is already mentioned in docker-compose.yml)
docker compose exec web python manage.py migrate

```

## Troubleshooting

- **WebSockets not connecting**: make sure you are running **Daphne** (or another ASGI server). `python manage.py runserver` won’t serve Channels WebSockets unless configured appropriately.
- **Static files missing**: run `python manage.py collectstatic` (especially when `DEBUG=False`).

