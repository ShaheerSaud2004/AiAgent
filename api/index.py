"""
Vercel serverless function entry point for FastAPI app.
This must export a 'handler' variable that Vercel can call.
"""
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Set environment for Vercel
os.environ.setdefault('PYTHONUNBUFFERED', '1')

# Import and wrap FastAPI app
try:
    from mangum import Mangum
    from main import app
    
    # Create Mangum handler - this converts ASGI to Lambda/Vercel format
    handler = Mangum(app, lifespan="off")
    
except Exception as e:
    # If import fails, create a minimal error handler
    import traceback
    from fastapi import FastAPI
    from mangum import Mangum
    
    error_app = FastAPI()
    
    @error_app.get("/")
    @error_app.post("/")
    async def error_handler():
        return {
            "error": "Application failed to load",
            "message": str(e),
            "traceback": traceback.format_exc()
        }
    
    handler = Mangum(error_app, lifespan="off")
