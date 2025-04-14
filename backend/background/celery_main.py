"""
Celery app configuration for asynchronous task processing.
"""

import os
import logging
from celery import Celery
from celery.signals import task_failure, task_success, task_retry
from config.settings import settings

# Setup logging
logger = logging.getLogger(__name__)

# Get Broker URL from settings
BROKER_URL = settings.CELERY_BROKER_URL

# Create Celery instance
celery_app = Celery(
    "literature_data_miner",
    broker=BROKER_URL,
    backend=BROKER_URL,
    include=["background.tasks"],
)

# Optional: Configure Celery
celery_app.conf.update(
    # Task result expiration - 2 days
    result_expires=172800,
    # Task time limit (seconds)
    task_time_limit=3600,
    # Maximum retries for tasks
    task_max_retries=3,
    # Retry delay (in seconds)
    task_retry_delay=30,
    # Acknowledgment late - helps prevent lost tasks
    task_acks_late=True,
    # Reject tasks when worker process dies
    task_reject_on_worker_lost=True,
    # Number of concurrent worker processes/threads
    worker_concurrency=2,
    # Prefetch multiplier - how many tasks a worker can reserve for itself
    worker_prefetch_multiplier=1,
    # Task serialization format
    task_serializer="json",
    # Result serialization format
    result_serializer="json",
    # Accept content types
    accept_content=["json"],
)


# Logging for Celery tasks
@task_failure.connect
def task_failure_handler(task_id, exception, args, kwargs, traceback, einfo, **kw):
    """Log task failures."""
    logger.error(
        f"Task {task_id} failed: {exception}\nArgs: {args}\nKwargs: {kwargs}",
        exc_info=True,
    )


@task_success.connect
def task_success_handler(sender=None, **kwargs):
    """Log task successes."""
    logger.info(f"Task {sender.request.id} completed successfully")


@task_retry.connect
def task_retry_handler(request, reason, einfo, **kwargs):
    """Log task retries."""
    logger.warning(f"Task {request.id} is being retried. Reason: {reason}")
