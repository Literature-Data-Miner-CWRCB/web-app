import logging
import logging.config
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from config.settings import settings
from api.v1.router import api_router
from background.celery_main import celery_app
from core.event_bus import event_bus

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(parents=True, exist_ok=True)

# Load logging configuration
logging.config.fileConfig("config/logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for the FastAPI app.
    """
    # Startup: Connect to Redis for event bus
    try:
        await event_bus.connect()
        logger.info("Event bus connected")
    except Exception as e:
        logger.error(f"Failed to connect to event bus: {str(e)}")

    yield

    # Shutdown: Clean up connections
    try:
        await event_bus.disconnect()
        logger.info("Cleaned up SSE connections")
    except Exception as e:
        logger.error(f"Error cleaning up SSE connections: {str(e)}")


app = FastAPI(
    title="Literature Data Miner API",
    description="Backend API for Literature Data Miner",
    version="0.1.0",
    lifespan=lifespan,
    openapi_url=settings.FASTAPI_API_V1_STR + "/openapi.json",
    docs_url=settings.FASTAPI_API_V1_STR + "/docs",
)

# Allow CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.FASTAPI_API_V1_STR)


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """
    Get the status of a Celery task by its ID.

    Args:
        task_id: The Celery task ID to check

    Returns:
        JSON response with task status information
    """
    try:
        task = celery_app.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": task.status,
        }

        # Include result if task is successful
        if task.successful():
            response["result"] = task.result

        # Include error information if task failed
        if task.failed():
            response["error"] = str(task.result)

        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error retrieving task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error retrieving task status: {str(e)}"
        )


@app.get("/tasks/{task_id}/revoke")
async def revoke_task(task_id: str, terminate: bool = False):
    """
    Revoke (cancel) a running Celery task.

    Args:
        task_id: The Celery task ID to revoke
        terminate: Whether to terminate the task if it's executing

    Returns:
        JSON response confirming the task has been revoked
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        return JSONResponse(
            content={"task_id": task_id, "revoked": True, "terminated": terminate}
        )
    except Exception as e:
        logger.error(f"Error revoking task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error revoking task: {str(e)}")


@app.get("/")
async def root():
    return {"message": "Welcome to the Web App API"}


@app.get("/health")
async def health_check():
    health_status = {"status": "healthy", "services": {}}

    # Check Celery/Redis connection
    try:
        celery_inspect = celery_app.control.inspect()
        ping_response = celery_inspect.ping()
        if ping_response:
            health_status["services"]["celery"] = "connected"
        else:
            health_status["services"]["celery"] = "disconnected"
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Celery health check failed: {e}", exc_info=True)
        health_status["services"]["celery"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status
