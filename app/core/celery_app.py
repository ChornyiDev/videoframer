from celery import Celery
from celery.signals import worker_process_init
from .config import get_settings

settings = get_settings()

celery_app = Celery(
    "video_processor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Kiev',
    enable_utc=True,
    
    # Task execution settings
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,  # Hard timeout
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,  # Soft timeout
    worker_max_tasks_per_child=settings.CELERY_MAX_TASKS_PER_CHILD,  # Restart worker after N tasks
    
    # Concurrency and queue settings
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,  # Process one task at a time
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,  # Number of worker processes
    
    # Task retry settings
    task_acks_late=True,  # Tasks are acknowledged after execution
    task_reject_on_worker_lost=True,  # Reject tasks if worker dies
    
    # Result settings
    task_ignore_result=False,  # We need results
    result_expires=3600,  # Results expire after 1 hour
    
    # Broker settings
    broker_connection_retry_on_startup=True,  # Enable connection retry on startup
    broker_connection_max_retries=None,  # Retry forever
)

@worker_process_init.connect
def init_worker(**kwargs):
    """Initialize worker process"""
    # Here you can add any initialization code that should run
    # when a worker process starts
    pass
