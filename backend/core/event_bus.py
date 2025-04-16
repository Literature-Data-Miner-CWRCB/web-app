from typing import Dict, Any, Optional, AsyncIterator, Callable
import json
import asyncio
import logging
from redis.asyncio import Redis
from config.settings import settings
from models.task import TaskStatusUpdate

logger = logging.getLogger(__name__)


class EventBus:
    """
    Event bus to handle publishing and subscribing to events using Redis Pub/Sub.
    Implements the Singleton pattern to ensure only one instance exists.
    """

    _instance = None
    RECONNECT_DELAY = 2.0  # Seconds to wait before reconnection attempts

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._redis: Optional[Redis] = None
        self._pubsub = None
        self._channels = {}
        self._running = False
        self._initialized = True
        self._connection_lock = asyncio.Lock()

    async def connect(self) -> None:
        """Connect to Redis with connection lock to prevent multiple simultaneous connections."""
        async with self._connection_lock:
            if self._redis is not None and self._pubsub is not None:
                return  # Already connected

            try:
                self._redis = Redis.from_url(
                    settings.redis_url, encoding="utf-8", decode_responses=True
                )
                self._pubsub = self._redis.pubsub()
                self._running = True
                logger.info("Connected to Redis event bus")
            except Exception as e:
                logger.error(f"Failed to connect to Redis event bus: {str(e)}")
                self._redis = None
                self._pubsub = None
                raise

    async def _ensure_connected(self) -> bool:
        """Ensure Redis connection is active, attempt reconnection if needed."""
        if self._redis is None or self._pubsub is None:
            try:
                await self.connect()
                return True
            except Exception as e:
                logger.error(f"Failed to reconnect to Redis: {str(e)}")
                return False

        # Test connection
        try:
            await self._redis.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis connection lost, attempting to reconnect: {str(e)}")
            self._redis = None
            self._pubsub = None
            try:
                await self.connect()
                # Resubscribe to channels
                if self._channels:
                    for channel in self._channels:
                        await self._pubsub.subscribe(channel)
                    logger.info(
                        f"Resubscribed to {len(self._channels)} channels after reconnection"
                    )
                return True
            except Exception as reconnect_error:
                logger.error(f"Failed to reconnect to Redis: {str(reconnect_error)}")
                return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        self._running = False
        if self._pubsub:
            try:
                await self._pubsub.unsubscribe()
                await self._pubsub.close()
            except Exception as e:
                logger.warning(f"Error during pubsub disconnect: {str(e)}")

        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f"Error during redis disconnect: {str(e)}")

        self._pubsub = None
        self._redis = None
        self._channels = {}
        logger.info("Disconnected from Redis event bus")

    async def publish(self, channel: str, message: Dict[str, Any]) -> bool:
        """Publish a message to a channel. Returns success status."""
        if not await self._ensure_connected():
            logger.error(f"Cannot publish to channel {channel}: not connected")
            return False

        try:
            # Serialize message to JSON string before publishing
            json_message = json.dumps(message)
            response = await self._redis.publish(channel, json_message)
            logger.debug(f"Published message to channel {channel}: {message}")
            return response > 0
        except Exception as e:
            logger.error(f"Failed to publish message to channel {channel}: {str(e)}")
            return False

    async def publish_task_update(self, update: TaskStatusUpdate) -> bool:
        """Publish a task status update. Returns success status."""
        task_specific_channel = f"{settings.TASK_STATUS_CHANNEL}:{update.task_id}"
        return await self.publish(
            channel=task_specific_channel, message=update.model_dump(mode="json")
        )

    async def subscribe(self, channel: str) -> bool:
        """Subscribe to a channel. Returns success status."""
        if not await self._ensure_connected():
            logger.error(f"Cannot subscribe to channel {channel}: not connected")
            return False

        try:
            await self._pubsub.subscribe(channel)
            self._channels[channel] = True
            logger.info(f"Subscribed to channel: {channel}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to channel {channel}: {str(e)}")
            return False

    async def listen(self) -> AsyncIterator[Dict[str, Any]]:
        """Listen for messages on subscribed channels with improved error handling."""
        if not self._pubsub:
            raise RuntimeError("Not subscribed to any channels")

        consecutive_errors = 0
        max_consecutive_errors = 5

        while self._running:
            try:
                if not await self._ensure_connected():
                    await asyncio.sleep(self.RECONNECT_DELAY)
                    continue

                message = await self._pubsub.get_message(ignore_subscribe_messages=True)
                if message:
                    channel = message.get("channel")
                    data = message.get("data")

                    parse_data = json.loads(data)
                    parse_data["channel"] = channel
                    print("parse_data", parse_data)
                    yield parse_data
                await asyncio.sleep(0.01)  # Small delay to avoid CPU spinning

            except asyncio.CancelledError:
                logger.info("Listen task was cancelled")
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    f"Error while listening for messages ({consecutive_errors}/{max_consecutive_errors}): {str(e)}"
                )

                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(
                        f"Too many consecutive errors ({consecutive_errors}), stopping listener"
                    )
                    yield {
                        "error": "EventBus listener stopped due to repeated errors",
                        "message": str(e),
                    }
                    break

                await asyncio.sleep(min(consecutive_errors * self.RECONNECT_DELAY, 10))

    async def subscribe_to_task_updates(self, task_id: Optional[str] = None) -> bool:
        """Subscribe to task status updates. Returns success status."""
        if task_id:
            channel = f"{settings.TASK_STATUS_CHANNEL}:{task_id}"
            return await self.subscribe(channel)
        else:
            return await self.subscribe(settings.TASK_STATUS_CHANNEL)


# Global instance
event_bus = EventBus()
