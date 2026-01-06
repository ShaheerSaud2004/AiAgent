"""
Vercel serverless function entry point for FastAPI app.
This file is the entry point for Vercel's serverless functions.
"""
import sys
import os

# Add parent directory to path so we can import main
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import the FastAPI app
from main import app

# Use Mangum to wrap FastAPI for AWS Lambda/Vercel compatibility
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")  # lifespan="off" because Vercel handles startup differently
except ImportError:
    # Fallback: export app directly (Vercel Python runtime may handle it)
    handler = app
