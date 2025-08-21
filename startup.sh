#!/bin/bash
# Azure App Service startup script for Linux
# Use the PORT environment variable provided by Azure, fallback to 8000
PORT=${PORT:-8000}
python -m gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:$PORT --timeout 600
