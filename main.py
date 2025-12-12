import os
import uvicorn
from fastapi import FastAPI

# NUCLEAR OPTION REDUX: The Exact Code That Worked Before

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Minimal Deployment (No Redis)"}

# CLI Entry Point - No __main__ needed
