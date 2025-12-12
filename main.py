import os
import uvicorn
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Minimal Deployment"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"Starting Minimal Server on PORT {port}...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
