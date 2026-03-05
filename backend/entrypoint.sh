#!/bin/sh
set -e

mkdir -p /app/media /app/staticfiles

if [ "$(id -u)" = "0" ]; then
    chown -R appuser:appuser /app/media /app/staticfiles
    exec gosu appuser "$@"
fi

exec "$@"
