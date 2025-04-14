#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

rm -f './celerybeat.pid'
celery -A background.celery_main beat --loglevel=info