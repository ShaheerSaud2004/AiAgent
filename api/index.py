import sys
import os

# Add parent directory
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent not in sys.path:
    sys.path.insert(0, parent)

# Import everything we need
from mangum import Mangum
from main import app

# Create the adapter
mangum_adapter = Mangum(app, lifespan="off")

# Handler function - must be at module level
def handler(event, context):
    """AWS Lambda handler for Vercel."""
    response = mangum_adapter(event, context)
    return response
