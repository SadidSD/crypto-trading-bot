from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis.asyncio as redis
import os
import json
import asyncio
import logging
from typing import List, Dict
from dotenv import load_dotenv

import sys

import sys

# Logging setup was problematic, simple print works reliably in Railway
def log(msg, error=False):
    prefix = "ERROR" if error else "INFO"
    print(f"{prefix}: {msg}", flush=True)

load_dotenv()

app = FastAPI(title="Exhaustion Bot API V2")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Models
class SettingsUpdate(BaseModel):
    sl_percentage: float
    tp1_percentage: float
    tp2_percentage: float
    max_trades_per_hour: int
    risk_per_trade: float

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {
            "market_updates": [],
            "trade_updates": [],
            "bot_status": [],
            "ai_signals": []
        }

    async def connect(self, websocket: WebSocket, channel: str):
        # WebSocket is already accepted in the endpoint
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        if websocket not in self.active_connections[channel]:
            self.active_connections[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.active_connections:
            self.active_connections[channel].remove(websocket)

    async def broadcast(self, message: dict, channel: str):
        if channel in self.active_connections:
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_json(message)
                except:
                    pass

manager = ConnectionManager()

# Background Task to stream Redis events to WebSockets
@app.on_event("startup")
@app.on_event("startup")
async def startup_event():
    log("Web API Startup...")
    # Check Redis
    try:
        await redis_client.ping()
        log("Web API Redis Connection: OK")
    except Exception as e:
        log(f"Web API Redis FAILED: {e}", error=True)
        
    # Start Subscriber
    asyncio.create_task(safe_subscriber_start())

async def safe_subscriber_start():
    try:
        await redis_subscriber()
    except Exception as e:
         log(f"Redis Subscriber Crash: {e}", error=True)

async def redis_subscriber():
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("bot_logs", "trade_events", "market_events")
    
    async for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            data = json.loads(message['data'])
            
            # Route to WS channels
            if channel == "bot_logs":
                await manager.broadcast(data, "bot_status")
            elif channel == "trade_events":
                await manager.broadcast(data, "trade_updates")
            elif channel == "market_events":
                await manager.broadcast(data, "market_updates")

# --- REST Endpoints ---

@app.get("/")
async def root():
    return {"message": "Exhaustion Bot API Online", "status": "ok"}

@app.get("/status")
async def get_status():
    status = await redis_client.get("bot_status") or "stopped"
    candidates = await redis_client.llen("scanner:candidates")
    
    # Mock Balance/PnL for now (or fetch if implemented)
    balance = 1000.0 # Placeholder
    pnl = 0.0 # Placeholder
    
    return {
        "status": status,
        "balance": balance,
        "today_pnl": pnl,
        "active_candidates": candidates
    }

@app.post("/control/start")
async def start_bot():
    await redis_client.set("bot_status", "active")
    await manager.broadcast({"type": "status_change", "status": "active"}, "bot_status")
    return {"status": "active"}

@app.post("/control/stop")
async def stop_bot():
    await redis_client.set("bot_status", "paused")
    await manager.broadcast({"type": "status_change", "status": "paused"}, "bot_status")
    return {"status": "paused"}

@app.post("/control/reset_ai")
async def reset_ai():
    # Clear AI cache logic here if needed
    return {"message": "AI Cache Cleared"}

@app.get("/trades")
async def get_trades(limit: int = 50):
    trades = await redis_client.lrange("trade_history", 0, limit - 1)
    return [json.loads(t) for t in trades]

@app.get("/positions")
async def get_positions():
    # In a real bot, we'd query Binance or local tracker
    # For now, return empty or mocked
    return [] 

@app.get("/logs")
async def get_logs(limit: int = 100):
    logs = await redis_client.lrange("bot_logs", 0, limit - 1)
    return [json.loads(l) for l in logs]

@app.get("/test_redis")
async def test_redis():
    try:
        await redis_client.ping()
        return {"status": "ok", "message": "Redis is Reachable"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/settings")
async def get_settings():
    # Default settings
    defaults = {
        "sl_percentage": 0.015,
        "tp1_percentage": 0.02,
        "tp2_percentage": 0.08,
        "max_trades_per_hour": 3,
        "risk_per_trade": 0.5
    }
    saved = await redis_client.get("bot_settings")
    if saved:
        return {**defaults, **json.loads(saved)}
    return defaults

@app.post("/settings/update")
async def update_settings(settings: SettingsUpdate):
    await redis_client.set("bot_settings", json.dumps(settings.dict()))
    await manager.broadcast({"type": "settings_update", "data": settings.dict()}, "bot_status")
    return {"message": "Settings updated"}

@app.get("/insights/news")
async def get_news_insights():
    # Mock or fetch real AI logs
    return {"sentiment": "neutral", "recent_headlines": []}

@app.get("/insights/heatmap")
async def get_heatmap():
    keys = await redis_client.keys("klines:*:4h")
    results = []
    
    for key in keys:
        try:
            # Key format: klines:BTC/USDT:4h
            symbol = key.split(":")[1]
            data_str = await redis_client.get(key)
            if not data_str: continue
            
            data = json.loads(data_str)
            if not data or len(data) < 1: continue
            
            # Latest candle
            latest = data[-1]
            open_p = float(latest[1])
            close_p = float(latest[4])
            
            if open_p == 0: continue
            
            change = ((close_p - open_p) / open_p) * 100
            
            results.append({
                "symbol": symbol,
                "value": round(change, 2),
                "price": close_p
            })
        except Exception:
            continue
            
    # Sort by absolute move magnitude (biggest movers first)
    results.sort(key=lambda x: abs(x['value']), reverse=True)
    return results[:50] # Return top 50 movers

# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Expect subscription message
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            # User sends {"action": "subscribe", "channels": ["market_updates"]}
            if data.get("action") == "subscribe":
                for channel in data.get("channels", []):
                    await manager.connect(websocket, channel)
    except WebSocketDisconnect:
        # Cleanup is tricky with multiple channels per socket logic above
        # Simplified: manager disconnects on broadcast error usually
        pass
