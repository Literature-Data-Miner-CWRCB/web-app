import logging
import traceback
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import asyncio

logger = logging.getLogger(__name__)


# WebSocket connection manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()  # For thread-safe operations

    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Accept a WebSocket connection and store it.

        Args:
            websocket: The WebSocket connection to accept
            client_id: The unique ID for the client
        """
        await websocket.accept()

        # Use a lock to avoid race conditions when multiple connections are handled
        async with self._lock:
            # Check if there's an existing connection for this client
            if client_id in self.active_connections:
                logger.warning(
                    f"Replacing existing WebSocket connection for client: {client_id}"
                )
                # Try to close the previous connection gracefully
                try:
                    await self.active_connections[client_id].close()
                except Exception:
                    pass  # Ignore errors when closing old connection

            # Store the new connection
            self.active_connections[client_id] = websocket

        logger.info(f"WebSocket client connected: {client_id}")

    async def disconnect(self, client_id: str):
        """
        Remove a client's WebSocket connection.

        Args:
            client_id: The unique ID for the client to disconnect
        """
        async with self._lock:
            if client_id in self.active_connections:
                # Try to close the connection gracefully
                try:
                    await self.active_connections[client_id].close()
                except Exception:
                    pass  # Ignore errors when closing

                # Remove from active connections
                del self.active_connections[client_id]
                logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_update(self, client_id: str, data: Dict[str, Any]):
        """
        Send an update to a client via WebSocket.

        Args:
            client_id: The unique ID for the client to send to
            data: The data to send

        Returns:
            bool: True if the message was sent successfully, False otherwise
        """
        async with self._lock:
            # First check if the client is connected
            if client_id not in self.active_connections:
                logger.warning(
                    f"Attempted to send message to non-existent client: {client_id}"
                )
                # Log all connected clients for debugging
                connected_clients = list(self.active_connections.keys())
                logger.debug(f"Currently connected clients: {connected_clients}")
                return False

            websocket = self.active_connections[client_id]

        # Send message outside the lock to prevent blocking
        try:
            # Validate the WebSocket connection is still open
            if websocket.client_state.CONNECTED:
                try:
                    await websocket.send_json(data)
                    return True
                except WebSocketDisconnect:
                    logger.info(
                        f"WebSocket disconnected while sending to client {client_id}"
                    )
                except Exception as e:
                    error_details = traceback.format_exc()
                    logger.error(
                        f"Error sending update to client {client_id}: {str(e)}\n{error_details}"
                    )
            else:
                logger.warning(f"WebSocket for client {client_id} is not connected")
        except Exception as e:
            # Catch-all for any unexpected errors
            error_details = traceback.format_exc()
            logger.error(
                f"Unexpected error with WebSocket for client {client_id}: {str(e)}\n{error_details}"
            )

        # If we reached here, message wasn't sent successfully
        # Let's remove this connection since it's likely not valid anymore
        await self.disconnect(client_id)
        return False

    async def broadcast(self, data: Dict[str, Any]):
        """
        Send an update to all connected clients.

        Args:
            data: The data to send to all clients
        """
        # Get a copy of client IDs to avoid modification during iteration
        async with self._lock:
            client_ids = list(self.active_connections.keys())

        # Send to each client
        for client_id in client_ids:
            await self.send_update(client_id, data)


# Create a singleton instance
connection_manager = ConnectionManager()
