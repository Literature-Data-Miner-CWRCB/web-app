FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    C_FORCE_ROOT=true

WORKDIR /app

# Install system dependencies and cleanup in one layer to reduce image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && \
    rm -rf ~/.cache/pip

# Copy entrypoint script and make it executable
COPY ./compose/dev/entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//g' /entrypoint.sh && chmod +x /entrypoint.sh

# Copy start script and make it executable
COPY ./compose/dev/start.sh /start.sh
RUN sed -i 's/\r$//g' /start.sh && chmod +x /start.sh

# Command to run the application
ENTRYPOINT ["/entrypoint.sh"]