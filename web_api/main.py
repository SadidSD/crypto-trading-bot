from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# PHASE 3: THE SKELETON API
# No Redis. No Lifespan. No Complex Routes.

app = FastAPI(title="Skeleton API")

# 1. Barebones Root
@app.get("/")
async def root():
    return {"status": "ok", "message": "Skeleton API is Alive"}

# 2. Simple Health Check
@app.get("/health")
async def health():
    return {"status": "healthy"}

# COMMENTED OUT EVERYTHING ELSE TO ISOLATE THE ROOT CAUSE
# redis_client = ...
# @app.middleware("http") ...
# CORSMiddleware ...
# Routes ...
