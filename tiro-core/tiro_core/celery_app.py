"""Configurazione Celery per task periodici e asincroni."""
from celery import Celery
from tiro_core.config import settings

celery = Celery(
    "tiro",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Rome",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Beat schedule — task periodici
celery.conf.beat_schedule = {
    "raccolta-posta-poll": {
        "task": "tiro_core.raccolta.posta.poll_email",
        "schedule": settings.imap_poll_interval_sec,
    },
    "raccolta-archivio-sync": {
        "task": "tiro_core.raccolta.archivio.sync_drive",
        "schedule": settings.gdrive_sync_interval_sec,
    },
}
