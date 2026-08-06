from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    'dineos',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.workers.tasks'],
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Kolkata',
    enable_utc=True,
    beat_schedule={
        'daily-digest-8am': {
            'task': 'send_daily_digest',
            'schedule': crontab(hour=8, minute=0),
        },
    },
)
