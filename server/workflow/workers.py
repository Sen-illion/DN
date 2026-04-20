from __future__ import annotations

from .config import WorkflowSettings

try:
    from celery import Celery
except Exception:
    Celery = None



def build_celery_app(settings: WorkflowSettings):
    if Celery is None:
        return None
    app = Celery(
        "dn_workflow",
        broker=settings.broker_url,
        backend=settings.result_backend,
    )
    app.conf.task_always_eager = settings.task_always_eager
    app.conf.task_default_queue = "queue:text.generate.high"
    return app
