"""
Celery tasks for asynchronous processing of data generation.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from celery import Task

# Local imports
from core.workers.celery_main import celery_app
from core.websockets.manager import connection_manager
from rag.main import DatasetGenerator
from utils.pydantic_utils import create_model_from_json

logger = logging.getLogger(__name__)


class WebSocketTask(Task):
    """Base task that includes WebSocket communication capabilities."""

    _loop = None

    @property
    def loop(self):
        """Get or create an event loop for WebSocket async operations."""
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        return self._loop

    async def _send_update(self, client_id: str, data: Dict[str, Any]):
        """Send an update via WebSocket."""
        try:
            await connection_manager.send_update(client_id, data)
        except Exception as e:
            logger.error(f"Failed to send WebSocket update to {client_id}: {str(e)}")

    def send_update(self, client_id: str, data: Dict[str, Any]):
        """Synchronous wrapper to send WebSocket updates from Celery tasks."""
        if client_id:
            future = asyncio.run_coroutine_threadsafe(
                self._send_update(client_id, data), self.loop
            )
            try:
                # Wait for the result with a timeout to avoid blocking indefinitely
                future.result(timeout=5)
            except Exception as e:
                logger.error(f"Error sending WebSocket update: {str(e)}")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure by sending a WebSocket notification."""
        client_id = kwargs.get("client_id")
        if client_id:
            error_msg = f"Task failed: {str(exc)}"
            self.send_update(
                client_id,
                {
                    "status": "error",
                    "message": error_msg,
                    "stage": "error",
                    "error": str(exc),
                    "progress": 0,
                    "total": 100,
                },
            )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(
    bind=True, base=WebSocketTask, max_retries=2, name="tasks.generate_dataset"
)
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

    # Report initial progress
    self.send_update(
        client_id,
        {
            "status": "started",
            "message": "Task started: initializing dataset generation",
            "progress": 0,
            "total": 100,
            "stage": "initialization",
        },
    )

    try:
        dataset_generator = DatasetGenerator()

        # Define the progress callback
        def progress_callback(data):
            """Callback function for reporting progress."""
            self.send_update(client_id, data)

        # Create the schema model from field definitions
        self.send_update(
            client_id,
            {
                "status": "processing",
                "message": "Creating dataset schema",
                "progress": 10,
                "total": 100,
                "stage": "schema_preparation",
            },
        )

        try:
            row_schema = create_model_from_json(
                field_definitions_json_str, model_name=model_name
            )
        except Exception as e:
            logger.error(f"Schema creation error: {str(e)}")
            raise ValueError(f"Invalid schema definition: {str(e)}")

        # Call the actual generator with the progress callback
        result = dataset_generator.generate(
            user_query, row_schema, rows=rows, progress_callback=progress_callback
        )

        # Send final completion message
        if result["success"]:
            self.send_update(
                client_id,
                {
                    "status": "completed",
                    "message": "Dataset generation complete",
                    "progress": 100,
                    "total": 100,
                    "stage": "completed",
                    "result": result,
                },
            )
            logger.info(
                f"Dataset generation completed successfully for client {client_id}"
            )
        else:
            self.send_update(
                client_id,
                {
                    "status": "error",
                    "message": "Failed to generate complete dataset",
                    "progress": 100,
                    "total": 100,
                    "stage": "error",
                    "error": "Dataset generation did not complete successfully",
                },
            )
            logger.warning(f"Dataset generation incomplete for client {client_id}")

        return result

    except Exception as e:
        logger.error(f"Dataset generation error: {str(e)}", exc_info=True)

        # Try to send error via WebSocket
        error_message = f"Error generating dataset: {str(e)}"
        self.send_update(
            client_id,
            {
                "status": "error",
                "message": error_message,
                "stage": "error",
                "error": str(e),
                "progress": 0,
                "total": 100,
            },
        )

        # Retry logic - retry up to max_retries with exponential backoff
        retries = self.request.retries
        max_retries = self.max_retries

        if retries < max_retries:
            logger.info(
                f"Retrying task for client {client_id} ({retries+1}/{max_retries})"
            )
            self.send_update(
                client_id,
                {
                    "status": "processing",
                    "message": f"Retrying dataset generation ({retries+1}/{max_retries})",
                    "progress": 0,
                    "total": 100,
                    "stage": "initialization",
                },
            )
            # Retry with exponential backoff
            raise self.retry(exc=e, countdown=2**retries * 30)
        else:
            # Final failure
            error_message = (
                f"Dataset generation failed after {max_retries} retries: {str(e)}"
            )
            self.send_update(
                client_id,
                {
                    "status": "error",
                    "message": error_message,
                    "stage": "error",
                    "error": str(e),
                    "progress": 0,
                    "total": 100,
                },
            )

        # Re-raise the exception to mark the task as failed
        raise
