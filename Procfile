api: uvicorn app.main:app --host 0.0.0.0 --port 8000
scheduler: python -m consumers.scheduler
dispatcher: python -m consumers.task_dispatcher
realtime: uvicorn consumers.realtime:app --host 0.0.0.0 --port 8001
celery: celery -A consumers.celery_app:celery_app worker --loglevel=INFO
