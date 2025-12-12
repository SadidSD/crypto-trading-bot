import os
import uvicorn
from web_api.main import app

if __name__ == "__main__":
    # Get PORT from environment (Railway sets this)
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Production API on PORT {port}...", flush=True)
    
    # Run Uvicorn directly (Standard Entry Point)
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="debug", 
        access_log=True,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
