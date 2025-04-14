#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

worker_ready() {
    celery -A background.celery_main inspect ping
}

until worker_ready; do
    >&2 echo "Celery workers not available"
    sleep 1
done
>&2 echo "Celery workers are available"

celery flower --app=background.celery_main --broker="${CELERY_BROKER_URL}"