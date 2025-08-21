# Root main.py file for Azure App Service compatibility
# This file imports the FastAPI app from the app module

from app.main import app

# This allows Azure to find the app at the root level
# while keeping our organized structure in the app/ directory
