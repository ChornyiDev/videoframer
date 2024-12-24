from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, HttpUrl
import httpx
import json
import logging
from .core.celery_app import celery_app
from .services.video_service import VideoProcessor
from .core.config import get_settings
from typing import Optional, Dict, Any

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="Video Processing API")

# Enable GZIP compression for API responses
if settings.ENABLE_GZIP:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

class VideoRequest(BaseModel):
    video_url: HttpUrl
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

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
        logger.error("No webhook URL configured")
        return False

    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Додаємо метадані до результату
        if "metadata" in result:
            logger.info(f"Adding metadata to result: {result['metadata']}")
            result.update(result["metadata"])
            del result["metadata"]

        logger.info(f"Sending webhook to {settings.WEBHOOK_URL}")
        logger.info(f"Webhook payload: {json.dumps(result, indent=2)}")
        
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                settings.WEBHOOK_URL,
                json=result,
                headers=headers
            )
            
        response.raise_for_status()
        logger.info(f"Webhook response: {response.status_code}")
        logger.info(f"Webhook response body: {response.text}")
        return True

    except Exception as e:
        logger.error(f"Error sending webhook: {str(e)}")
        if isinstance(e, httpx.HTTPError):
            logger.error(f"HTTP Status: {e.response.status_code if hasattr(e, 'response') else 'Unknown'}")
            logger.error(f"Response body: {e.response.text if hasattr(e, 'response') else 'Unknown'}")
        return False

@celery_app.task(name="process_video_task")
def process_video_task(video_url: str, system_prompt: str | None = None, metadata: dict | None = None):
    """Process video task"""
    logger.info(f"Starting video processing task for URL: {video_url}")
    if metadata:
        logger.info(f"With metadata: {metadata}")
    
    try:
        processor = VideoProcessor()
        logger.info("Initialized VideoProcessor")
        
        result = processor.process_video(video_url, system_prompt)
        logger.info("Video processing completed")
        
        if metadata:
            result["metadata"] = metadata
            logger.info("Added metadata to result")
            
        if send_to_webhook(result):
            logger.info("Webhook sent successfully")
        else:
            logger.error("Failed to send webhook")
            
        return result
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}", exc_info=True)
        raise

@app.post("/process")
async def process_video(request: VideoRequest):
    """Process video endpoint"""
    logger.info(f"Received request to process video: {request.video_url}")
    try:
        task = process_video_task.delay(
            str(request.video_url),
            request.system_prompt,
            request.metadata
        )
        logger.info(f"Created Celery task with ID: {task.id}")
        return {"task_id": task.id, "status": "Processing started"}
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """Get task status endpoint"""
    logger.info(f"Checking status for task: {task_id}")
    try:
        task = celery_app.AsyncResult(task_id)
        response = {
            "task_id": task_id,
            "status": task.status,
        }
        
        if task.status == 'SUCCESS':
            response["result"] = task.result
        elif task.status == 'FAILURE':
            response["error"] = str(task.result)
            
        logger.info(f"Task status: {response}")
        return response
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {"status": "healthy"}
