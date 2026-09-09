#!/bin/sh
set -e

# alembic.ini's script_location is "backend/alembic", relative to the repo
# root -- alembic must be invoked from /srv (not /srv/backend) to resolve it.
cd /srv

echo "Running database migrations..."
alembic -c backend/alembic.ini upgrade head

# The app itself (YOLODetector's default model_path="yolov8n.pt", and the
# evidence/ directory) expects to be run with cwd=backend/, matching local
# `cd backend && uvicorn ...` dev usage -- switch there now that migrations
# (which needed cwd=/srv) are done.
cd backend

exec "$@"
