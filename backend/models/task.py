from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Optional
from datetime import datetime, timezone


class TaskStatus(str, Enum):
    """Enum for task status."""

    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"


class TaskStage(BaseModel):
    """Model for task stage information."""
    status: TaskStatus
    description: Optional[str] = None


class TaskStatusUpdate(BaseModel):
    """Model for task status updates that will be sent through events."""

    task_id: str
    status: TaskStatus
    stage: Optional[TaskStage] = None
    message: Optional[str] = None

class TaskInfo(BaseModel):
    """Task info model."""

    task_id: str
    status: TaskStatus
    current_stage: Optional[TaskStage] = None
    result: Optional[Any] = None
