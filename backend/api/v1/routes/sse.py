from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import json
import logging
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
from core.event_bus import event_bus
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Keep track of active connections for healthcheck
active_connections = 0


async def event_generator(
    request: Request, task_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for task updates.
    If task_id is provided, subscribe only to that task's updates.
    Otherwise, subscribe to all task updates.
    """
    global active_connections
    active_connections += 1

    # Format SSE message
    def format_sse_message(data: Dict[str, Any]) -> str:
        json_data = json.dumps(data)
        return f"data: {json_data}\n\n"

    # Send a ping to keep connection alive
    async def send_ping():
        return format_sse_message(
            {"type": "ping", "timestamp": asyncio.get_event_loop().time()}
        )

    # First message to confirm connection
    yield format_sse_message({"type": "connected", "task_id": task_id})

    # Keep track of subscription success
    subscription_success = False

    try:
        # Subscribe to task updates
        if task_id:
            subscription_success = await event_bus.subscribe_to_task_updates(task_id)
            if not subscription_success:
                yield format_sse_message(
                    {
                        "type": "error",
                        "error": f"Failed to subscribe to updates for task {task_id}",
                    }
                )
        else:
            subscription_success = await event_bus.subscribe_to_task_updates()
            if not subscription_success:
                yield format_sse_message(
                    {"type": "error", "error": "Failed to subscribe to task updates"}
                )

        # Set up ping timer
        ping_interval = 30  # seconds
        last_ping_time = asyncio.get_event_loop().time()

        # Main event loop
        async for message in event_bus.listen():
            current_time = asyncio.get_event_loop().time()

            # Check for client disconnection
            if await request.is_disconnected():
                logger.info(
                    f"Client disconnected from SSE stream {'for task ' + task_id if task_id else ''}"
                )
                break

            # Send periodic pings to keep connection alive
            if current_time - last_ping_time > ping_interval:
                yield await send_ping()
                last_ping_time = current_time

            # Handle error messages from event_bus
            if "error" in message:
                logger.warning(f"Error from event bus: {message.get('error')}")
                yield format_sse_message(
                    {
                        "type": "error",
                        "error": message.get("error"),
                        "message": message.get(
                            "message", "Unknown error in event stream"
                        ),
                    }
                )
                continue

            # Only forward messages for the requested task_id if specified
            if task_id and message.get("task_id") != task_id:
                continue

            # Add message type for better client handling
            if "type" not in message:
                message["type"] = "task_update"

            yield format_sse_message(message)

            # If the task is in a final state, close the connection
            if task_id and message.get("status") in ["SUCCESS", "FAILURE", "REVOKED"]:
                logger.info(
                    f"Task {task_id} reached final state {message.get('status')}, closing SSE connection"
                )
                # Send final message
                yield format_sse_message(
                    {
                        "type": "connection_closing",
                        "reason": f"Task {task_id} completed with status {message.get('status')}",
                    }
                )
                break

    except asyncio.CancelledError:
        logger.info(
            f"SSE connection cancelled {'for task ' + task_id if task_id else ''}"
        )
        yield format_sse_message(
            {"type": "cancelled", "message": "Connection cancelled"}
        )
    except Exception as e:
        logger.error(f"Error in SSE event generator: {str(e)}", exc_info=True)
        # Yield error message to client
        yield format_sse_message(
            {
                "type": "error",
                "error": "Server error in event stream",
                "message": str(e),
            }
        )
    finally:
        active_connections -= 1
        logger.info(f"SSE connection closed {'for task ' + task_id if task_id else ''}")


@router.get("/events")
async def stream_events(request: Request) -> StreamingResponse:
    """Stream all task events."""
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Prevents Nginx from buffering the response
            "Content-Type": "text/event-stream",
        },
    )


@router.get("/events/{task_id}")
async def stream_task_events(request: Request, task_id: str) -> StreamingResponse:
    """Stream events for a specific task."""
    return StreamingResponse(
        event_generator(request, task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Prevents Nginx from buffering the response
            "Content-Type": "text/event-stream",
        },
    )


@router.get("/health")
async def sse_health() -> Dict[str, Any]:
    """Health check endpoint for SSE connections."""
    redis_connected = False
    try:
        # Test Redis connection
        if event_bus._redis:
            await event_bus._redis.ping()
            redis_connected = True
    except Exception:
        pass

    return {
        "status": "healthy" if redis_connected else "degraded",
        "active_connections": active_connections,
        "redis_connected": redis_connected,
    }


# Helper function for middleware to close SSE connections properly
async def cleanup_sse_connections():
    """Clean up SSE connections when the application shuts down."""
    try:
        await event_bus.disconnect()
        logger.info("Cleaned up SSE connections")
    except Exception as e:
        logger.error(f"Error cleaning up SSE connections: {str(e)}")
