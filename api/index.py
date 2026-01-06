"""
Vercel serverless function entry point for FastAPI app.
Creates a proper Lambda handler function for Vercel.
"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set environment for Vercel
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Import Mangum and FastAPI app
from mangum import Mangum
from main import app

# Create Mangum handler
mangum_handler = Mangum(app, lifespan="off")

# Create a Lambda-compatible handler function
# Vercel expects a function that takes (event, context)
def handler(event, context):
    """
    Lambda handler function for Vercel.
    This is the format Vercel's Python runtime expects.
    """
    return mangum_handler(event, context)
