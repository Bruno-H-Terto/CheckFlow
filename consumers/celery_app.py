# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

from celery import Celery

from config.settings import settings


celery_app = Celery(
    "checkflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["consumers.tasks"],
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_track_started=True,
)
