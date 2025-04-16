from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime, timezone


class TaskStatus(str, Enum):
    """Enum for task status."""

    PENDING = "pending"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REVOKED = "revoked"


class TaskStatusUpdate(BaseModel):
    """Model for task status updates that will be sent through events."""

    task_id: str = Field(..., description="The ID of the task")
    status: TaskStatus = Field(..., description="The status of the task")
    message: Optional[str] = Field(
        None, description="The message of the task to be displayed to the user"
    )
