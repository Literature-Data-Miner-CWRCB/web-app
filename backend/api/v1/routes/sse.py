from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import logging
import asyncio
from typing import Optional, AsyncGenerator
from core.event_bus import event_bus
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def event_generator(
    request: Request, task_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for task updates.
    If task_id is provided, subscribe only to that task's updates.
    Otherwise, subscribe to all task updates.
    """
    # Subscribe to task updates
    try:
        if task_id:
            await event_bus.subscribe_to_task_updates(task_id)
        else:
            await event_bus.subscribe_to_task_updates()

        async for message in event_bus.listen():
            if await request.is_disconnected():
                logger.info(
                    f"Client disconnected from SSE stream {'for task ' + task_id if task_id else ''}"
                )
                break

            # Only forward messages for the requested task_id if specified
            if task_id and message.get("task_id") != task_id:
                continue

            yield json.dumps(message)

            # If the task is in a final state, close the connection
            if task_id and message.get("status") in ["SUCCESS", "FAILURE", "REVOKED"]:
                logger.info(
                    f"Task {task_id} reached final state {message.get('status')}, closing SSE connection"
                )
                break

    except Exception as e:
        logger.error(f"Error in SSE event generator: {str(e)}")
        # Yield error message to client
        yield json.dumps({"error": "Server error in event stream", "message": str(e)})
    finally:
        logger.info(f"SSE connection closed {'for task ' + task_id if task_id else ''}")


@router.get("/events")
async def stream_events(request: Request) -> StreamingResponse:
    """Stream all task events."""
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/events/{task_id}")
async def stream_task_events(request: Request, task_id: str) -> StreamingResponse:
    """Stream events for a specific task."""
    return StreamingResponse(
        event_generator(request, task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# Helper function for middleware to close SSE connections properly
async def cleanup_sse_connections():
    """Clean up SSE connections when the application shuts down."""
    try:
        await event_bus.disconnect()
        logger.info("Cleaned up SSE connections")
    except Exception as e:
        logger.error(f"Error cleaning up SSE connections: {str(e)}")
