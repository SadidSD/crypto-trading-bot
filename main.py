import asyncio
import os
import redis.asyncio as redis
from dotenv import load_dotenv

# Import modules
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
        await collector.run() # This fetches data
        await scanner.scan() # This filters and pushes to queue
        print("--- Cycle Complete. Waiting 15m ---")
        await asyncio.sleep(900) # 15 minutes

async def main():
    r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
    
    # Initialize components
    collector = MarketCollector()
    scanner = MarketScanner()
    engine = DecisionEngine()
    executor = TradeExecutor()
    
    # Create Tasks
    # 1. Collector/Scanner Loop (Periodic)
    data_task = asyncio.create_task(run_collector_scanner(collector, scanner, r))
    
    # 2. Decision Engine (Continuous Consumer)
    engine_task = asyncio.create_task(engine.run())
    
    # 3. Execution Engine (Continuous Consumer)
    exec_task = asyncio.create_task(executor.run())

    # 4. Web API Server (Railway Port Binding)
    port = int(os.getenv("PORT", 8000))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    api_task = asyncio.create_task(server.serve())
    
    await asyncio.gather(data_task, engine_task, exec_task, api_task)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot Stopped.")
