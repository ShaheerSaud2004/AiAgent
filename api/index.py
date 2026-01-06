from mangum import Mangum
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import FastAPI app
from main import app

# Create Mangum adapter
adapter = Mangum(app, lifespan="off")

# Export handler function - Vercel requires this exact format
def handler(event, context):
    return adapter(event, context)
