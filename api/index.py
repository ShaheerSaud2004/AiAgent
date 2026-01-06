"""
Vercel serverless function entry point.
Minimal handler to avoid Vercel runtime issues.
"""
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import dependencies
from mangum import Mangum

# Import app - do this last to catch any import errors
try:
    from main import app
except Exception as e:
    # Create minimal error app if import fails
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/")
    async def error():
        return {"error": f"Import failed: {str(e)}"}

# Create handler - must be a function, not a class instance
mangum_app = Mangum(app, lifespan="off")

def handler(event, context):
    """Lambda handler - Vercel expects this exact signature."""
    try:
        return mangum_app(event, context)
    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Handler error: {str(e)}"
        }
