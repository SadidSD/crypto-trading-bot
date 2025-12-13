import os
import asyncio
import json
import logging
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

# Import Core Engines
# These imports work because we run from the project root (server.py)
try:
    from collector.collector import MarketCollector
    from scanner.scanner import MarketScanner
    from engine.decision import DecisionEngine
    from execution.executor import TradeExecutor
    from monitoring.telegram_bot import start_telegram_bot # Import Bot
    IMPORTS_OK = True
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    IMPORTS_OK = False

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("API")

# Redis Config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}"

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS Client Connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WS Client Disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.error(f"WS Broadcast Error: {e}")

manager = ConnectionManager()
redis_client = None

# Background Task References
collector = None
scanner = None
engine = None
executor = None

async def scanner_loop(scanner_instance):
    logger.info("Scanner Loop Started")
    while True:
        try:
            status = await redis_client.get("bot_status")
            if status == "active":
                logger.info("Running Scan...")
                await scanner_instance.scan()
            else:
                logger.info("Scanner Idle (Bot Paused)")
            
            await asyncio.sleep(60 * 15) # Scan every 15 Minutes
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Scanner Loop Error: {e}")
            await asyncio.sleep(60)

# --- Lifespan Manager (The Brain) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, collector, scanner, engine, executor
    
    logger.info(">>> STARTING BOT SYSTEMS <<<")
    
    # Debug: Print Registered Routes
    logger.info("--- REGISTERED ROUTES ---")
    for route in app.routes:
        if isinstance(route, APIRoute):
            logger.info(f"ROUTE: {route.methods} {route.path}")
        else:
            logger.info(f"ROUTE: {route.path} ({type(route)})")
    logger.info("-------------------------")

    # 1. Connect Redis
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis Connected Successfully")
    except Exception as e:
        logger.error(f"Redis Connection Failed: {e}")

    # 1.5 Start Telegram Bot
    if IMPORTS_OK:
        start_telegram_bot()

    # 2. Start Engines (only if imports worked)
    if IMPORTS_OK:
        collector = MarketCollector()
        scanner = MarketScanner()
        engine = DecisionEngine()
        executor = TradeExecutor()
        
        # Launch Background Loops
        # These run concurrently in the event loop
        asyncio.create_task(collector.run())     # Data Collection Loop
        asyncio.create_task(engine.run())        # Decision Engine Loop
        asyncio.create_task(executor.run())      # Trade Execution Loop
        asyncio.create_task(scanner_loop(scanner)) # Scanner Loop
        
        logger.info("All Bot Engines Launched.")
    else:
        logger.warning("ENGINES NOT STARTED DUE TO IMPORT ERRORS")
    
    yield # API Runs Here
    
    logger.info(">>> SHUTTING DOWN BOT SYSTEMS <<<")
    if collector: await collector.close()
    if executor: await executor.close()
    if redis_client: await redis_client.close()

# --- FastAPI App ---
app = FastAPI(title="Exhaustion Bot API", description="Trading Bot Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow ALL origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

@app.get("/")
async def root():
    return {
        "status": "online",
        "system": "Exhaustion Bot",
        "components": ["Collector", "Scanner", "Engine", "Executor"] if IMPORTS_OK else ["IMPORTS_FAILED"]
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/status")
async def get_status():
    if not redis_client: return {"status": "error", "detail": "Redis Disconnected"}
    status = await redis_client.get("bot_status") or "offline"
    return {"status": status}

@app.post("/control/start")
async def start_bot():
    logger.info("ENDPOINT CALL: /control/start")
    if not redis_client: return {"error": "No Redis"}
    await redis_client.set("bot_status", "active")
    await manager.broadcast({"type": "status_change", "status": "active"})
    return {"status": "active"}

@app.post("/control/stop")
async def stop_bot():
    logger.info("ENDPOINT CALL: /control/stop")
    if not redis_client: return {"error": "No Redis"}
    await redis_client.set("bot_status", "offline")
    await manager.broadcast({"type": "status_change", "status": "offline"})
    return {"status": "offline"}

# Heatmap Endpoint for Dashboard
@app.get("/insights/heatmap")
async def get_heatmap():
    if not redis_client: return []
    try:
        keys = await redis_client.keys("metrics:*")
        data = []
        for k in keys:
            symbol = k.split(":")[1]
            # OLD: raw = await redis_client.get(k); m = json.loads(raw)
            # NEW: Redis Hash
            m = await redis_client.hgetall(k)
            
            if m:
                # Prefer change_24h (Stream) -> change_4h (Poll) -> 0
                change_val = float(m.get("change_24h", m.get("change_4h", 0)))
                
                data.append({
                    "symbol": symbol,
                    "value": round(change_val, 2),
                    "price": float(m.get("price", 0))
                })
        return data
    except Exception as e:
        logger.error(f"Heatmap Error: {e}")
        return []

@app.get("/debug/system")
async def debug_system():
    stats = {
        "redis_connected": bool(redis_client),
        "components": {
            "collector": bool(collector),
            "scanner": bool(scanner),
            "engine": bool(engine),
            "executor": bool(executor)
        },
        "env": {
            "binance_key_set": bool(os.getenv("BINANCE_API_KEY")),
            "redis_host": REDIS_HOST
        },
        "data_counts": {}
    }
    
    if redis_client:
        try:
            stats["data_counts"]["metrics"] = len(await redis_client.keys("metrics:*"))
            stats["data_counts"]["klines"] = len(await redis_client.keys("klines:*"))
            stats["data_counts"]["orders"] = await redis_client.llen("execution:orders")
            stats["bot_status"] = await redis_client.get("bot_status")
        except Exception as e:
            stats["redis_error"] = str(e)
            
    return stats

@app.post("/debug/trade")
async def debug_trade():
    """Injects a FAKE signal to test execution (Demo Trade)"""
    if not redis_client: return {"error": "No Redis"}
    
    # Test Signal: Long TRX (Safer/Cheaper than BTC)
    signal = {
        "symbol": "TRXUSDT",
        "side": "BUY",
        "amount": 20, # ~$6 USD value (Safe test size)
        "params": {
            "stop_loss": 0.20, 
            "take_profit_1": 0.35,
            "take_profit_2": 0.40
        },
        "scores": {"debug": 100}
    }
    
    await redis_client.lpush("execution:orders", json.dumps(signal))
    logger.info(" injected DEBUG signal")
    return {"status": "injected", "signal": signal}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Log connection attempt
    logger.info(f"WS Attempt from {websocket.client}")
    # Explicitly accept
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            # Keep connection open
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WS Error: {e}")
