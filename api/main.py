import sys
import os

# Add parent to path
parent = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent)

# Import using importlib to avoid naming conflict
import importlib.util
spec = importlib.util.spec_from_file_location("app_main", os.path.join(parent, "main.py"))
app_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_main)
app = app_main.app

# Use Mangum
from mangum import Mangum
mangum_handler = Mangum(app, lifespan="off")

# Export handler - Vercel will auto-detect Python
def handler(event, context):
    return mangum_handler(event, context)
