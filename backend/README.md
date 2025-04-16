# Literature Data Miner Backend

## Asynchronous Task Processing with Celery and Redis

This application uses Celery with Redis for asynchronous task processing, enabling scalable and reliable handling of long-running operations such as dataset generation.

### Architecture Overview

The application implements a task queue architecture with the following components:

1. **FastAPI Web Server**: Handles HTTP requests, WebSocket connections, and task management
2. **Redis**: Acts as both the message broker and result backend
3. **Celery Workers**: Process tasks asynchronously
4. **WebSockets**: Provide real-time updates to clients

### Key Features

- **Task Persistence**: Tasks survive application restarts or crashes
- **Automatic Retries**: Failed tasks are automatically retried with exponential backoff
- **Real-time Progress Updates**: WebSockets provide live task status to clients
- **Task Management**: APIs for checking status and canceling tasks
- **Scalability**: Multiple workers can process tasks in parallel

### Implementation Details

#### Task Processing Flow

1. Client submits a dataset generation request via the `/api/v1/datasets/generate` endpoint
2. The request is validated and a Celery task is queued with a unique client ID
3. The client receives an immediate response with the task ID and WebSocket URL
4. The client establishes a WebSocket connection to receive progress updates
5. A Celery worker picks up the task and begins processing
6. The worker sends progress updates via WebSocket during processing
7. When complete, the worker sends the final result or error information

#### WebSocket Communication

The WebSocketTask base class provides utilities for sending updates from Celery tasks. Key aspects:

- Manages async event loops for WebSocket communication
- Includes error handling and timeouts
- Task-level exceptions caught and reported

#### Server-Sent Events (SSE)

The application now supports Server-Sent Events alongside WebSockets for real-time updates:

- SSE provides a simpler, unidirectional communication channel from server to client
- More efficient for scenarios where clients only need to receive updates
- Better browser compatibility and can work through proxies more easily
- Automatic reconnection handled by the browser

The SSEManager handles:
- Client connection management with multiple connections per client ID
- Robust error handling and cleanup of disconnected clients
- Async queue-based messaging to prevent blocking

Both WebSockets and SSE can be used simultaneously for improved reliability:
- Updates are sent through both channels when available
- Clients can choose their preferred method or use both as fallbacks for each other
- Consistent message format across both protocols

To connect to SSE:
```
GET /sse/{client_id}
```

#### Error Handling

The implementation includes comprehensive error handling:

- **Task-level Exceptions**: Caught and reported via WebSockets
- **Automatic Retries**: Tasks retry automatically with exponential backoff (30s, 60s, 120s)
- **Graceful Degradation**: Clients receive error details if tasks fail
- **Timeout Protection**: WebSocket sends have timeouts to prevent blocking

#### Task Monitoring and Control

The API provides endpoints for task management:

- `GET /tasks/{task_id}`: Check task status and results
- `GET /tasks/{task_id}/revoke`: Cancel a running task

### Configuration

Redis connection parameters are configurable via environment variables:

- `REDIS_HOST`: Redis server hostname (default: "redis")
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_PASSWORD`: Redis password if required (default: "")

### Deployment Considerations

#### Scaling

For higher throughput:

1. Increase the number of Celery worker containers in docker-compose
2. Adjust Celery's `worker_concurrency` setting based on CPU resources
3. Consider Redis clustering for very high workloads

#### Production Readiness

For production deployments:

1. Enable Redis persistence (AOF and RDB) 
2. Configure Redis authentication
3. Implement a Redis health check in the Celery worker
4. Add task result monitoring and clean-up
5. Consider using Celery Flower for task monitoring UI

### Example: Task Status Updates

Task status updates sent via WebSocket follow this format:

```json
{
  "status": "processing",
  "message": "Creating dataset schema",
  "progress": 10,
  "total": 100,
  "stage": "schema_preparation"
}
```

Status values include:
- "started": Initial task state
- "processing": Task is being processed
- "completed": Task completed successfully
- "error": Task failed with an error 

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/datasets/generate' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'user_query=water%20treatment%20technologies%20used%20in%20specialty%20crop%20production&rows=5&model_name=TreatmentTechnologies&field_definitions_json_str=%5B%7B%22name%22%3A%22technology_id%22%2C%22type%22%3A%22str%22%2C%22description%22%3A%22Unique%20identifier%20for%20water%20treatment%20technology%22%2C%22required%22%3Atrue%7D%2C%7B%22name%22%3A%22technology_name%22%2C%22type%22%3A%22str%22%2C%22description%22%3A%22Name%20of%20water%20treatment%20technology%22%2C%22required%22%3Atrue%7D%5D&client_id=test-client-id-1'
```

