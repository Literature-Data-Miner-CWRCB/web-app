"""
Celery tasks for asynchronous processing of data generation.
"""

import traceback
import logging
import asyncio
from typing import Dict, Any, Optional
from pydantic import create_model
from celery import Task

# Local imports
from background.celery_main import celery_app
from core.websocket_manager import connection_manager
from core.pipelines.dataset_generation import DatasetGenerator
from utils.pydantic_utils import convert_to_row_model

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """Base task that includes WebSocket communication capabilities."""

    def send_update(self, client_id: str, data: Dict[str, Any]):
        """Synchronous wrapper to send WebSocket updates from Celery tasks."""
        if not client_id:
            return

        try:
            # Create a new event loop for this specific update
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Run the async operation in the new loop
                loop.run_until_complete(connection_manager.send_update(client_id, data))
            finally:
                # Ensure the loop is closed properly
                loop.close()

        except Exception as e:
            logger.error(
                f"Error sending WebSocket update to client {client_id}: {str(e)}\n"
            )

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

        # Call the actual generator with the progress callback
        row_model = convert_to_row_model(
            field_definitions_json_str=field_definitions_json_str
        )
        dataset_generator = DatasetGenerator(row_model=row_model)
        result = dataset_generator.generate(
            query=user_query, rows=rows, progress_callback=progress_callback
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
        error_details = traceback.format_exc()
        logger.error(
            f"Dataset generation error: {str(e)}\n{error_details}", exc_info=True
        )

        # Send error via WebSocket
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

        # Re-raise the exception to mark the task as failed
        raise
