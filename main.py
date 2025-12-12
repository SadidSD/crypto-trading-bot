import os
import uvicorn
import traceback
from fastapi import FastAPI
from fastapi.responses import JSONResponse

# DIAGNOSTIC MODE V3: The Error Catcher
try:
    print("Attempting to import Real Web API...", flush=True)
    from web_api.main import app
    print("Import Successful!", flush=True)
except Exception as e:
    print("CRITICAL: IMPORT FAILED", flush=True)
    traceback.print_exc()
    
    # Fallback App to report the error via HTTP
    app = FastAPI()
    error_msg = traceback.format_exc()
    
    @app.get("/{path:path}")
    async def catch_all(path: str):
        return JSONResponse(
            status_code=200, # Return 200 so we can see the message content
            content={
                "status": "CRITICALLY_BROKEN",
                "error_type": str(type(e)),
                "error_message": str(e),
                "traceback": error_msg.split("\n")
            }
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Diagnostic Server on PORT {port}...", flush=True)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="debug", 
        access_log=True, 
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
