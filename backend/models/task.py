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

    name: str
    description: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def complete(self) -> None:
        """Mark the stage as completed."""
        self.completed_at = datetime.now(timezone.utc)


class TaskStatusUpdate(BaseModel):
    """Model for task status updates that will be sent through events."""

    task_id: str
    status: TaskStatus
    stage: Optional[TaskStage] = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now(timezone.utc))


class TaskInfo(BaseModel):
    """Task info model."""

    task_id: str
    status: TaskStatus
    current_stage: Optional[TaskStage] = None
    result: Optional[Any] = None
    created_at: datetime = Field(default_factory=datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=datetime.now(timezone.utc))
