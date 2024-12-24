from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, HttpUrl
import httpx
import json
from .core.celery_app import celery_app
from .services.video_service import VideoProcessor
from .core.config import get_settings
from typing import Optional

settings = get_settings()

app = FastAPI(title="Video Processing API")

# Enable GZIP compression for API responses
if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

class VideoRequest(BaseModel):
    video_url: HttpUrl  # Validates URL format
    system_prompt: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "video_url": "https://example.com/video.mp4",
                "system_prompt": "Optional custom prompt for video description"
            }
        }

def send_to_webhook(result: dict) -> bool:
    """Send result to webhook with better error handling"""
    if not settings.WEBHOOK_URL:
        return False

    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        print(f"Sending webhook to {settings.WEBHOOK_URL}")
        print(f"Webhook payload: {json.dumps(result, indent=2)}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                settings.WEBHOOK_URL,
                json=result,
                headers=headers
            )
            
            print(f"Webhook response status: {response.status_code}")
            print(f"Webhook response body: {response.text}")
            
            response.raise_for_status()
            return True
            
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            print(f"HTTP Status: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
            print(f"Response body: {e.response.text if hasattr(e, 'response') else 'Unknown'}")
        return False

@celery_app.task(name="process_video")
def process_video_task(video_url: str, system_prompt: str | None = None):
    processor = VideoProcessor()
    result = processor.process_video(video_url, system_prompt)
    
    # Send result to webhook
    if settings.WEBHOOK_URL:
        success = send_to_webhook(result)
        if not success:
            result['webhook_error'] = "Failed to send webhook"
    
    return result

@app.post("/process")
async def process_video(request: VideoRequest):
    try:
        # Start async task
        task = process_video_task.delay(str(request.video_url), request.system_prompt)
        return {
            "status": "processing",
            "task_id": task.id,
            "message": "Video processing started. Results will be sent to webhook."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
