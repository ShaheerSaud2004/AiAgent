"""
Vercel serverless function entry point for FastAPI app.
"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set environment for Vercel
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Import the FastAPI app
try:
    from main import app
    handler = app
except Exception as e:
    # Create a minimal error handler if import fails
    from fastapi import FastAPI
    error_app = FastAPI()
    
    @error_app.get("/")
    async def error():
        return {"error": f"Import error: {str(e)}"}
    
    handler = error_app
