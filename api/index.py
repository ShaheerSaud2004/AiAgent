"""
Vercel serverless function entry point for FastAPI app.
Uses Mangum to wrap FastAPI for AWS Lambda/Vercel compatibility.
"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set environment for Vercel
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Import Mangum first
from mangum import Mangum

# Import the FastAPI app
try:
    from main import app
    # Wrap FastAPI app with Mangum for Vercel/Lambda compatibility
    handler = Mangum(app, lifespan="off")
except Exception as e:
    # Fallback: create minimal error app
    from fastapi import FastAPI
    error_app = FastAPI()
    
    @error_app.get("/")
    async def error():
        return {"error": f"Import error: {str(e)}", "type": type(e).__name__}
    
    handler = Mangum(error_app, lifespan="off")
