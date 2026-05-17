import sys
from pathlib import Path

from celery import Celery
from celery.schedules import crontab

# Add parent directory to Python path so judge module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings

celery_app = Celery(
    "online_judge",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "workers.judge_task",
        "workers.grade_sync_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_pool="solo",
    task_max_retries=3,
    task_default_retry_delay=30,
    result_expires=3600,
    beat_schedule={},
)
