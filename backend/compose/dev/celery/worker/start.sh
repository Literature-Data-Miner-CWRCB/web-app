#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Run celery worker with better configuration
celery -A background.celery_main worker \
    --loglevel=info \
    --concurrency=${CELERY_WORKER_CONCURRENCY:-4} \
    --max-tasks-per-child=${CELERY_MAX_TASKS_PER_CHILD:-100} \
    --max-memory-per-child=${CELERY_MAX_MEMORY_PER_CHILD:-500000} \
    --without-gossip \
    --without-mingle \
    --task-events \
    --hostname=worker@%h