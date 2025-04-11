#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

rm -f './celerybeat.pid'
celery -A core.workers.celery_main beat --loglevel=info