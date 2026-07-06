# Kelaasor Video Streaming

This is an independent FastAPI microservice dedicated to handling heavy video processing workloads (FFprobe/FFmpeg) and serving HLS video streams. It acts as a companion service to the `kelaasor_back` Django monolith.

## Architecture & Responsibilities

- **Video Processing:** Exposes a secure API endpoint to queue video processing tasks. The heavy lifting (transcoding) is offloaded to a Celery worker to avoid blocking the main web server.
- **Shared Resources:** Shares the SQLite database (`db.sqlite3`) and filesystem storage (`media/` directory) with the main Django backend.
- **HLS Serving:** Directly serves the generated `.m3u8` playlists and `.ts` video segments to frontend clients.
- **Webhooks:** Notifies the Django monolith when a video finishes processing or fails.

## Prerequisites

Before running this project, ensure you have the following installed on your system:
- **Python 3.10+**
- **FFmpeg & FFprobe:** Must be installed and accessible in your system's PATH.
- **Redis:** Required as the message broker for Celery.

## Setup & Installation

1. **Navigate to the project directory:**
   ```bash
   cd E:\ForNow\Programming\kelaasor_video_streaming
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install the dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The application uses `pydantic-settings` to manage configuration. You can create a `.env` file in the root directory to override the defaults. 

Key environment variables:
- `FASTAPI_API_KEY`: Secret key required to authenticate API requests from Django. (Default: `default_secret_api_key_for_dev`)
- `DATABASE_URL`: Connection string for the shared database. (Default: `sqlite:///E:/path/to/kelaasor_back/db.sqlite3`)
- `REDIS_URL`: Connection string for Redis. (Default: `redis://localhost:6379/0`)
- `DJANGO_WEBHOOK_URL`: The URL in Django to send processing status updates. (Default: `http://127.0.0.1:8000/api/webhooks/video-status/`)
- `MEDIA_DIR`: The absolute path to the shared media directory. (Default: `E:/path/to/kelaasor_back/media`)

## Running the Service

To run this microservice fully, you need to start both the FastAPI server and the Celery worker process.

### 1. Start the FastAPI Web Server
Run the Uvicorn server (typically on port 8001 so it doesn't conflict with Django):
```bash
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### 2. Start the Celery Worker
In a separate terminal (with the virtual environment activated), start the Celery worker to process the queued videos. 
*(Note: On Windows, use `-P threads` or `-P solo` as shown below. The `gevent` library currently lacks pre-built wheels for Python 3.13+).*
```bash
celery -A worker.celery_app worker --loglevel=info -P threads
```

## API Endpoints

### `POST /api/v1/videos/process`
Queues a video for HLS transcoding.
- **Headers:** 
  - `X-API-Key`: Your configured `FASTAPI_API_KEY`
- **Body:** 
  ```json
  {
      "media_id": 123
  }
  ```
- **Response:** `202 Accepted`

### `GET /media/hls/{media_id}/master.m3u8`
Serves the generated HLS files directly (Static mount).

## Directory Structure
- `main.py`: FastAPI application setup, middleware, static mounts, and API routes.
- `worker.py`: Celery app initialization and the heavy FFmpeg/FFprobe transcoding pipeline.
- `models.py`: SQLAlchemy models that map to the shared database tables.
- `database.py`: SQLAlchemy engine and session management.
- `config.py`: Environment and configuration management.
