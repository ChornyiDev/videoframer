from app.core.celery_app import celery_app
from app.main import process_video_task

if __name__ == '__main__':
    celery_app.start()
