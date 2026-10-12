#!/usr/bin/env bash
set -euo pipefail

python deploy/check_render_test_source.py
python manage.py check --deploy --fail-level ERROR

case "${1:-web}" in
  web)
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
    exec python -m gunicorn DjangoProject.wsgi:application \
      --bind "0.0.0.0:${PORT:-10000}" --workers 1 --threads 2 \
      --timeout 120 --access-logfile - --error-logfile -
    ;;
  worker)
    ready=0
    for attempt in $(seq 1 60); do
      if python manage.py migrate --check >/dev/null 2>&1; then
        ready=1
        break
      fi
      sleep 2
    done
    if [ "$ready" -ne 1 ]; then
      echo "Test database is not ready. Wait for the web migration, then redeploy this worker." >&2
      exit 1
    fi
    exec python manage.py process_video_jobs
    ;;
  *)
    echo "Choose web or worker." >&2
    exit 1
    ;;
esac
