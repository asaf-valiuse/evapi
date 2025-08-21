#!/bin/bash
# Azure App Service startup script
python -m gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 --timeout 600
