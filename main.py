import os
import uvicorn
import traceback
from fastapi import FastAPI

# FINAL DIAGNOSTIC: Minimal + Error Catching

app = FastAPI(title="Exhaustion Bot API (Diagnostic)")

@app.get("/")
async def root():
    print("DEBUG: Root Endpoint Hit", flush=True)
    return {"status": "ok", "message": "Diagnostic API is Alive"}

if __name__ == "__main__":
    try:
        raw_port = os.getenv("PORT", "8080")
        port = int(raw_port)
        print(f"DEBUG: STARTING ON PORT {port} (Raw Env: {raw_port})", flush=True)
        
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print("CRITICAL: MAIN CRASHED", flush=True)
        traceback.print_exc()
