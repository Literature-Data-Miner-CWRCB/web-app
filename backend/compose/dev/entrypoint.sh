#!/bin/bash

# Set Python path to include /app (the mounted volume)
export PYTHONPATH=/app

# Make sure directory structure exists
mkdir -p /app/logs

exec "$@"