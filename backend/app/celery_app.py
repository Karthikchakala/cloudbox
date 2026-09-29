import os
from celery import Celery

def make_celery(app_name="cloudbox_tasks"):
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_password = os.getenv("REDIS_PASSWORD", "")
    
    auth_part = f":{redis_password}@" if redis_password else ""
    
    broker_url = os.getenv("CELERY_BROKER_URL")
    if not broker_url:
        broker_url = f"redis://{auth_part}{redis_host}:{redis_port}/1"
    elif redis_password and "@" not in broker_url:
        broker_url = broker_url.replace("redis://", f"redis://{auth_part}")

    result_backend = os.getenv("CELERY_RESULT_BACKEND")
    if not result_backend:
        result_backend = f"redis://{auth_part}{redis_host}:{redis_port}/2"
    elif redis_password and "@" not in result_backend:
        result_backend = result_backend.replace("redis://", f"redis://{auth_part}")

    celery_instance = Celery(
        app_name,
        broker=broker_url,
        backend=result_backend,
        include=["app.tasks.file_tasks"]
    )

    celery_instance.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=180,  # 3 minutes maximum per task
        worker_prefetch_multiplier=1,
        task_acks_late=True,
    )
    return celery_instance

celery = make_celery()
