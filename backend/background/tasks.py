"""
Celery tasks for asynchronous processing of data generation.
"""

import traceback
import logging
import asyncio
import json
import time
from typing import Dict, Any, Optional
from celery import Task

# Local imports
from background.celery_main import celery_app
from core.rag.extraction import StructuredExtractor
from core.pipelines.dataset_generation import DatasetGenerator
from utils.pydantic_utils import (
    convert_to_row_model,
    wrap_row_schema_with_citations,
    create_dataset_model,
)
from core.event_bus import event_bus
from models.task import TaskStatus, TaskStatusUpdate
from config.settings import settings

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """
    Custom Celery Task class that handles progress reporting.
    Enables tasks to send real-time updates via the EventBus.
    """
    abstract = True
    _event_loop = None
    _max_update_retries = 2

    def get_event_loop(self):
        """Get or create an event loop for async operations."""
        if self._event_loop is None or self._event_loop.is_closed():
            try:
                self._event_loop = asyncio.get_event_loop()
            except RuntimeError:
                # Create a new event loop if there's none
                self._event_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    def run_in_executor(self, func, *args, **kwargs):
        """Run a synchronous function in an executor to avoid blocking the event loop."""
        loop = self.get_event_loop()
        return loop.run_in_executor(None, func, *args, **kwargs)

    def _send_update(
        self, status: TaskStatus, message: Optional[str] = None, retry=0
    ) -> bool:
        """
        Send a task status update with retry mechanism.
        Returns True if the update was sent successfully, False otherwise.
        If no clients are connected, returns True without sending the update.
        """
        update = TaskStatusUpdate(
            task_id=str(self.request.id),
            status=status,
            message=message,
        )

        # Create an event loop or use the existing one
        loop = self.get_event_loop()

        try:
            # First check if there are any active clients connected
            has_clients = loop.run_until_complete(
                self._check_for_active_clients(update.task_id)
            )

            # If no clients are connected, log this and return success (no need to retry)
            if not has_clients:
                logger.debug(
                    f"No active clients for task {update.task_id}, skipping status update"
                )
                return True

            # Otherwise, try to send the update
            success = loop.run_until_complete(event_bus.publish_task_update(update))

            if not success and retry < self._max_update_retries:
                # Wait and retry with exponential backoff
                backoff_time = 0.5 * (2**retry)
                logger.warning(
                    f"Failed to send task update, retrying in {backoff_time:.2f}s (attempt {retry+1}/{self._max_update_retries})"
                )
                time.sleep(backoff_time)
                return self._send_update(status, message, retry + 1)

            if not success and retry >= self._max_update_retries:
                logger.error(f"Failed to send task update after {retry} retries")

            return success
        except Exception as e:
            logger.error(f"Failed to send task update: {str(e)}", exc_info=True)
            return False

    async def _check_for_active_clients(self, task_id: str) -> bool:
        """
        Check if there are any clients subscribed to updates for this task.
        Returns True if there are active clients, False otherwise.
        """
        task_specific_channel = f"{settings.TASK_STATUS_CHANNEL}:{task_id}"
        try:
            # Use the Redis API to check if there are any subscribers to this channel
            if not await event_bus._ensure_connected():
                return False

            subscribers = await event_bus._redis.pubsub_numsub(task_specific_channel)
            # subscribers returns a list of tuples (channel_name, subscriber_count)
            return subscribers and subscribers[0][1] > 0
        except Exception as e:
            logger.warning(f"Failed to check for active clients: {str(e)}")
            # In case of error, default to sending updates
            return True

    def set_state(self, task_status: TaskStatus, message: Optional[str] = None) -> bool:
        """
        Set the current state of the task and send an update.
        Returns True if the update was sent successfully, False otherwise.
        """
        return self._send_update(task_status, message)

    def on_success(self, retval, task_id, args, kwargs) -> None:
        """Handler called on task success."""
        success = self._send_update(
            TaskStatus.COMPLETED, message="Task completed successfully"
        )
        if not success:
            logger.warning(f"Failed to send success update for task {task_id}")
        super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        """Handler called on task failure."""
        error_message = f"Task failed: {str(exc)}"
        success = self._send_update(TaskStatus.FAILED, message=error_message)
        if not success:
            logger.warning(f"Failed to send failure update for task {task_id}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(bind=True, base=BaseTask, name="tasks.generate_dataset")
def generate_dataset_task(
    self,
    user_query: str,
    rows: int,
    model_name: str,
    field_definitions_json_str: str,
    client_id: str,
) -> Dict[str, Any]:
    """
    Celery task to generate a dataset based on the provided query and schema.

    Args:
        user_query: The user's natural language query
        rows: Number of rows to generate
        model_name: Name for the schema model
        field_definitions_json_str: JSON string defining the schema fields
        client_id: Client ID for WebSocket communication

    Returns:
        Dictionary containing generation results and metadata
    """
    logger.info(f"Starting dataset generation task for client {client_id}")

    try:
        self.set_state(TaskStatus.STARTED, message="Task started")
        time.sleep(10)

        self.set_state(
            TaskStatus.IN_PROGRESS, message="Processing query and data schema ..."
        )
        row_model = convert_to_row_model(
            field_definitions_json_str=field_definitions_json_str
        )
        row_model_with_citations = wrap_row_schema_with_citations(row_model=row_model)
        dataset_model = create_dataset_model(row_model=row_model_with_citations)
        extractor = StructuredExtractor(dataset_model)

        self.set_state(
            TaskStatus.IN_PROGRESS, message="Retrieving and extracting data ..."
        )
        extracted_items = extractor.extract(query=user_query)

        self.set_state(
            TaskStatus.IN_PROGRESS, message="Preparing data for the dataset ..."
        )
        # TODO: Prepare data for the dataset

        return {
            "success": True,
            "data": extracted_items.model_dump(),
        }

    except Exception as e:
        error_details = traceback.format_exc()
        error_message = f"Dataset generation error: {str(e)}"
        logger.error(f"{error_message}\n{error_details}", exc_info=True)

        self.set_state(
            TaskStatus.FAILED, message="Something went wrong. Try again later."
        )

        return {
            "success": False,
            "error": str(e),
        }
