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

async def run_collector_scanner(collector, scanner, r):
    while True:
        # Check Status (Dashboard Control)
        status = await r.get("bot_status")
        if status != "active":
             print(f"Bot Status is {status}. Waiting...")
             await asyncio.sleep(5)
             continue

        # Check Kill Switch
        ks = await r.get("bot:kill_switch")
        if ks == "1":
            print("Kill Switch Active. Pausing Data Collection.")
            await asyncio.sleep(60)
            continue

        print("--- Starting Data Cycle ---")
        try:
             await collector.run() # This fetches data
             await scanner.scan() # This filters and pushes to queue
        except Exception as e:
             print(f"CRITICAL DATA CYCLE ERROR: {e}")
             # Push to Redis for visibility
             try:
                 await r.lpush("bot_logs", f'{{"timestamp": "{os.getenv("TIMESTAMP_PLACEHOLDER")}", "message": "Data Cycle Crash: {str(e)}", "type": "error"}}')
             except: pass
        
        print("--- Cycle Complete. Waiting 5m ---")
        await asyncio.sleep(300) # 5 minutes

async def safe_engine_run(engine):
    try:
        await engine.run()
    except Exception as e:
        print(f"CRITICAL ENGINE CRASH: {e}")

async def safe_executor_run(executor):
    try:
        await executor.run()
    except Exception as e:
        print(f"CRITICAL EXECUTOR CRASH: {e}")

async def check_redis(r):
    try:
        print("Checking Redis connection...", flush=True)
        await r.ping()
        print("Redis Alive!", flush=True)
        return True
    except Exception as e:
        print(f"Redis Connection Failed: {e}", flush=True)
        return False

async def heartbeat():
    while True:
        print(f"HEARTBEAT [{datetime.now().time()}] - Event Loop Alive", flush=True)
        await asyncio.sleep(10)

async def main():
    print("Initializing Main...", flush=True)
    r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True, socket_timeout=5.0)
    
    if not await check_redis(r):
        print("FATAL: Redis not reachable. Exiting.", flush=True)
        # We don't exit to keep Uvicorn alive for logs, but we warn
    
    # Initialize components
    print("Initializing Components...", flush=True)
    collector = MarketCollector()
    scanner = MarketScanner()
    engine = DecisionEngine()
    executor = TradeExecutor()
    
    # Create Tasks
    # 1. Collector/Scanner Loop (Periodic)
    # No wrapper needed for data loop as it has internal try/except block now, 
    # but let's wrap the whole task just in case wrapper itself fails?
    # Actually, run_collector_scanner has while True. If it crashes, it stops.
    # We should wrap it to Restart?
    # For now, let's just make sure it doesn't kill main()
    
    async def safe_data_loop():
        try:
            await run_collector_scanner(collector, scanner, r)
        except Exception as e:
             print(f"DATA LOOP DEATH: {e}")

    data_task = asyncio.create_task(safe_data_loop())
    
    # 2. Decision Engine (Continuous Consumer)
    engine_task = asyncio.create_task(safe_engine_run(engine))
    
    # 3. Execution Engine (Continuous Consumer)
    exec_task = asyncio.create_task(safe_executor_run(executor))

    # 4. Web API Server (Railway Port Binding)
    port = int(os.getenv("PORT", 8000))
    # ENABLE PROXY HEADERS FOR RAILWAY
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=port, 
        port=port, 
        log_level="debug", # Verbose logs to catch request attempts
        access_log=True, 
        proxy_headers=True, 
        forwarded_allow_ips="*"
    )
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())
    
    # api_task already created above
    # api_task = asyncio.create_task(server.serve()) 
    # Duplicate removed. 
    # But wait, looking at lines 124 and 126 in view_file:
    # 124: api_task = asyncio.create_task(server.serve())
    # 125: 
    # 126: api_task = asyncio.create_task(server.serve())
    # We need to remove line 126 completely.
    heartbeat_task = asyncio.create_task(heartbeat())
    
    print("Tasks Created. Gathering...", flush=True)
    await asyncio.gather(data_task, engine_task, exec_task, api_task, heartbeat_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Stopped.")
