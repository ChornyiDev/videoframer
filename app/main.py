from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, HttpUrl
import httpx
import json
from .core.celery_app import celery_app
from .services.video_service import VideoProcessor
from .core.config import get_settings
from typing import Optional, Dict, Any

settings = get_settings()

app = FastAPI(title="Video Processing API")

# Enable GZIP compression for API responses
if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

class VideoRequest(BaseModel):
    video_url: HttpUrl  # Validates URL format
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Додаткові параметри

    class Config:
        json_schema_extra = {
            "example": {
                "video_url": "https://example.com/video.mp4",
                "system_prompt": "Optional custom prompt for video description",
                "metadata": {
                    "Post Rec ID": "rec203Zwfn0lV9u7G",
                    "Config Rec ID": "recEMgrOdYxMK5UvP",
                    "User Rec ID": "rec7q2YUCwU4aZn29"
                }
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

        # Додаємо метадані до результату
        if "metadata" in result:
            result.update(result["metadata"])
            del result["metadata"]

        print(f"Sending webhook to {settings.WEBHOOK_URL}")
        print(f"Webhook payload: {json.dumps(result, indent=2)}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                settings.WEBHOOK_URL,
                json=result,
                headers=headers
            )
            
        response.raise_for_status()
        print(f"Webhook response: {response.status_code}")
        return True

    except Exception as e:
        print(f"Error sending webhook: {str(e)}")
        return False

@celery_app.task(name="process_video_task")
def process_video_task(video_url: str, system_prompt: str | None = None, metadata: dict | None = None):
    """Process video task"""
    try:
        processor = VideoProcessor()
        result = processor.process_video(video_url, system_prompt)
        
        if metadata:
            result["metadata"] = metadata
            
        if send_to_webhook(result):
            print("Webhook sent successfully")
        else:
            print("Failed to send webhook")
            
        return result
    except Exception as e:
        print(f"Error processing video: {str(e)}")
        raise

@app.post("/process")
async def process_video(request: VideoRequest):
    """
    Process video endpoint
    """
    try:
        task = process_video_task.delay(
            str(request.video_url),
            request.system_prompt,
            request.metadata
        )
        return {"task_id": task.id, "status": "Processing started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
