from __future__ import annotations

from functools import lru_cache

from .config import WorkflowSettings
from .orchestrator import WorkflowOrchestrator
from .redis_store import RedisLeaseStore
from .sql_store import SqliteWorkflowRepository


@lru_cache(maxsize=1)
def get_workflow_service() -> WorkflowOrchestrator:
    settings = WorkflowSettings.from_env()
    repository = SqliteWorkflowRepository(settings.database_path)
    lease_store = RedisLeaseStore.from_settings(settings)
    return WorkflowOrchestrator(settings=settings, repository=repository, lease_store=lease_store)
