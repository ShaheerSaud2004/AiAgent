import sys
import os

# Add parent directory to path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent not in sys.path:
    sys.path.insert(0, parent)

# Import Mangum and FastAPI app
# Note: We import from the root main.py file
from mangum import Mangum
import importlib.util

# Load the root main.py module
spec = importlib.util.spec_from_file_location("app_main", os.path.join(parent, "main.py"))
app_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_main)

# Get the FastAPI app
app = app_main.app

# Create Mangum adapter
mangum_adapter = Mangum(app, lifespan="off")

# Handler function for Vercel
def handler(event, context):
    return mangum_adapter(event, context)
