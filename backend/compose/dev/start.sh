#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Memory-optimized settings
WORKERS=1  # Reduce from $(nproc) to control memory usage

# Start with production settings (no reload) to prevent memory issues
uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers $WORKERS \
    --limit-concurrency 50 \
    --no-access-log \
    --timeout-keep-alive 30 \
    --no-use-colors \
    --log-level info
