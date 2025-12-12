import asyncio
import os
import redis.asyncio as redis
from dotenv import load_dotenv

# Import modules
from datetime import datetime
from collector.collector import MarketCollector
from scanner.scanner import MarketScanner
from engine.decision import DecisionEngine
from execution.executor import TradeExecutor
from web_api.main import app
import uvicorn

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")

async def heartbeat():
    while True:
        print(f"HEARTBEAT [{datetime.now().time()}] - Event Loop Alive", flush=True)
        await asyncio.sleep(10)

async def main():
    print("Initializing Main (Web API Only)...", flush=True)
    
    # 4. Web API Server (Railway Port Binding)
    port = int(os.getenv("PORT", 8080))
    print(f"DEBUG: STARTING SERVER ON PORT: {port}", flush=True)
    
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=port, 
        log_level="debug", 
        access_log=True, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())
    heartbeat_task = asyncio.create_task(heartbeat())
    
    print("Tasks Created. Gathering (API + Heartbeat)...", flush=True)
    await asyncio.gather(api_task, heartbeat_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Stopped.")
