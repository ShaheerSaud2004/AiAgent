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
    try:
        return mangum_handler(event, context)
    except Exception as e:
        import traceback
        error_msg = f"Handler error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # This will show in Vercel logs
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": error_msg
        }
