import os
import uvicorn
from fastapi import FastAPI

# FINAL ATTEMPT: Respecting the Platform Contract

# IMPORT THE REAL APP
from web_api.main import app

# NOTE: The app object is now imported from web_api.main
# We do not define a dummy app here.

if __name__ == "__main__":
    # Railway provides the PORT variable. We MUST use it.
    # Default to 8080 only if testing locally.
    port_str = os.getenv("PORT", "8080")
    port = int(port_str)
    
    print(f"DEBUG: Railway Assigned PORT: {port}", flush=True)
    
    # Run simple, clean execution
    uvicorn.run(app, host="0.0.0.0", port=port)
