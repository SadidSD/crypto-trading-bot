import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# FLATTENED STRUCTURE: Defining App INLINE
# This bypasses any package import issues with 'web_api'

app = FastAPI(title="Exhaustion Bot API (Flattened)")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Flattened API is Alive"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Flattened Server on PORT {port}...", flush=True)
    
    # SIMPLIFIED STARTUP (Matching the working "Hello World" config)
    uvicorn.run(app, host="0.0.0.0", port=port)
