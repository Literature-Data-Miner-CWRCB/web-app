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
from core.pipelines.dataset_generation import DatasetGenerator
from utils.pydantic_utils import convert_to_row_model
from core.event_bus import event_bus
from models.task import TaskStatus, TaskStatusUpdate

logger = logging.getLogger(__name__)

class BaseTask(Task):
    """
    Custom Celery Task class that handles progress reporting.
    Enables tasks to send real-time updates via the EventBus.
    """
    abstract = True
    _current_stage: Optional[str] = None
    _event_loop = None
    _max_update_retries = 3

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

    def send_update(
        self, status: TaskStatus, message: Optional[str] = None, retry=0
    ) -> bool:
        """
        Send a task status update with retry mechanism.
        Returns True if the update was sent successfully, False otherwise.
        """
        update = TaskStatusUpdate(
            task_id=str(self.request.id),
            status=status,
            stage=self._current_stage,
            message=message,
            timestamp=time.time(),
        )

        # Create an event loop or use the existing one
        loop = self.get_event_loop()

        # Run the coroutine to publish the update
        try:
            success = loop.run_until_complete(event_bus.publish_task_update(update))

            if not success and retry < self._max_update_retries:
                # Wait and retry with exponential backoff
                backoff_time = 0.5 * (2**retry)
                logger.warning(
                    f"Failed to send task update, retrying in {backoff_time:.2f}s (attempt {retry+1}/{self._max_update_retries})"
                )
                time.sleep(backoff_time)
                return self.send_update(status, message, retry + 1)

            if not success and retry >= self._max_update_retries:
                logger.error(f"Failed to send task update after {retry} retries")

            return success
        except Exception as e:
            if retry < self._max_update_retries:
                # Wait and retry with exponential backoff
                backoff_time = 0.5 * (2**retry)
                logger.warning(
                    f"Error sending task update: {str(e)}, retrying in {backoff_time:.2f}s (attempt {retry+1}/{self._max_update_retries})"
                )
                time.sleep(backoff_time)
                return self.send_update(status, message, retry + 1)

            logger.error(f"Failed to send task update: {str(e)}")
            return False

    def set_stage(self, stage_name: str, message: Optional[str] = None) -> bool:
        """
        Set the current stage of the task and send an update.
        Returns True if the update was sent successfully, False otherwise.
        """
        success = self.send_update(TaskStatus.PROGRESS, message=message)

        if success:
            logger.info(f"Task {self.request.id} entered stage: {stage_name}")
        else:
            logger.warning(
                f"Task {self.request.id} entered stage {stage_name} but failed to send update"
            )

        return success

    def update_progress(
        self, current: int, total: int, message: Optional[str] = None
    ) -> bool:
        """
        Update the progress of the current task stage.
        Returns True if the update was sent successfully, False otherwise.
        """
        if total <= 0:
            percentage = 0
        else:
            percentage = min(100, max(0, int((current / total) * 100)))

        progress_update = TaskStatusUpdate(
            task_id=str(self.request.id),
            status=TaskStatus.PROGRESS,
            stage=self._current_stage,
            message=message or f"Progress: {percentage}%",
            progress={"current": current, "total": total, "percentage": percentage},
            timestamp=time.time(),
        )

        loop = self.get_event_loop()
        try:
            success = loop.run_until_complete(
                event_bus.publish_task_update(progress_update)
            )
            if success:
                logger.debug(f"Task {self.request.id} progress: {percentage}%")
            else:
                logger.warning(
                    f"Failed to send progress update for task {self.request.id}"
                )
            return success
        except Exception as e:
            logger.error(f"Error sending progress update: {str(e)}")
            return False

    def on_success(self, retval, task_id, args, kwargs) -> None:
        """Handler called on task success."""
        success = self.send_update(
            TaskStatus.SUCCESS, message="Task completed successfully"
        )
        if not success:
            logger.warning(f"Failed to send success update for task {task_id}")
        super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        """Handler called on task failure."""
        error_message = f"Task failed: {str(exc)}"
        success = self.send_update(TaskStatus.FAILURE, message=error_message)
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
        # Report task started
        self.set_stage(TaskStatus.STARTED, message="Task started")

        # Parse the field definitions
        try:
            field_definitions = json.loads(field_definitions_json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid field definitions JSON: {str(e)}")
            raise ValueError(f"Invalid field definitions JSON: {str(e)}")

        row_model = convert_to_row_model(
            field_definitions_json_str=field_definitions_json_str
        )
        dataset_generator = DatasetGenerator(row_model=row_model)

        # # Track progress for each 10% of rows
        # progress_interval = max(1, rows // 10)

        # def progress_callback(current_row: int):
        #     if current_row % progress_interval == 0 or current_row == rows:
        #         self.update_progress(
        #             current=current_row,
        #             total=rows,
        #             message=f"Generated {current_row}/{rows} rows",
        #         )

        # Call the actual generator with the progress callback
        result = dataset_generator.generate(
            query=user_query, rows=rows, progress_callback=None
        )

        # Format the result to match the frontend's expected structure
        formatted_result = {
            "rows": result.get("items", {}).get("rows", []),
            "schema": [
                {"name": field_def["name"], "type": field_def["type"]}
                for field_def in field_definitions
            ],
            "citations": result.get("items", {}).get("citations", []),
        }

        logger.info(f"Dataset generation completed successfully for client {client_id}")
        return formatted_result

    except Exception as e:
        error_details = traceback.format_exc()
        error_message = f"Dataset generation error: {str(e)}"
        logger.error(f"{error_message}\n{error_details}", exc_info=True)

        raise
