import logging
import json
import uuid
from typing import Annotated, List, Dict, Type, Optional
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import JSONResponse
from background.tasks import generate_dataset_task

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate")
async def generate_dataset(
    user_query: Annotated[str, Form(description="User query")],
    rows: Annotated[int, Form(description="Number of rows to generate")],
    model_name: Annotated[str, Form(description="Model name for the row schema")],
    field_definitions_json_str: Annotated[
        str, Form(description="Field definitions in JSON format")
    ],
) -> JSONResponse:
    """
    API endpoint to initiate dataset generation.

    This endpoint queues a Celery task that will generate the dataset based on the
    provided query and schema. Real-time progress updates are sent via WebSocket.

    Args:
        user_query: Natural language query describing the dataset to generate
        rows: Number of rows to generate in the dataset
        model_name: Name to use for the Pydantic model
        field_definitions_json_str: JSON string defining the schema fields

    Returns:
        JSONResponse with task information and WebSocket details

    Raises:
        HTTPException: If there's an error in the request parameters
    """
    try:
        # TODO: replace with user client id
        client_id = str(uuid.uuid4())

        # Validate input parameters
        if rows <= 0:
            raise ValueError("Number of rows must be greater than zero")

        if not user_query.strip():
            raise ValueError("User query cannot be empty")

        logger.info(f"Generating dataset with model: {model_name}, rows: {rows}")

        # Queue the Celery task
        task = generate_dataset_task.delay(
            user_query=user_query,
            rows=rows,
            model_name=model_name,
            field_definitions_json_str=field_definitions_json_str,
            client_id=client_id,
        )

        logger.info(
            f"Dataset generation task queued with ID: {task.id} for client: {client_id}"
        )

        # Return immediately with response containing task info and client_id
        return JSONResponse(
            content={
                "task_id": task.id,
            }
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Error initiating dataset generation: {e}", exc_info=True)
        return JSONResponse(
            content={"message": f"Server error: {str(e)}"}, status_code=500
        )
