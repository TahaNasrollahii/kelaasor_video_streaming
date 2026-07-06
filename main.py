from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from worker import process_video_task
import os

app = FastAPI(title="Kelaasor Video Streaming")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != settings.FASTAPI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return api_key

class ProcessVideoRequest(BaseModel):
    media_id: int

@app.post("/api/v1/videos/process", status_code=202)
def process_video(request: ProcessVideoRequest, api_key: str = Depends(verify_api_key)):
    process_video_task.delay(request.media_id)
    return {"message": "Video processing queued", "media_id": request.media_id}

# Mount the static directory to serve HLS files directly
hls_dir = os.path.join(settings.MEDIA_DIR, 'hls')
os.makedirs(hls_dir, exist_ok=True)
app.mount("/media/hls", StaticFiles(directory=hls_dir), name="hls")
