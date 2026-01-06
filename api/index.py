"""
Vercel serverless function entry point for FastAPI app.
"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the FastAPI app
from main import app

# Vercel expects the app to be exported
# For FastAPI with Vercel Python runtime, we export the app directly
# The @vercel/python runtime will handle it
handler = app
