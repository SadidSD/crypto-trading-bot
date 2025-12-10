import asyncio
import json
import os
import redis.asyncio as redis
import aiohttp
from dotenv import load_dotenv

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
BASE_URL = "https://fapi.binance.com" # Using Mainnet for Price Data (Scanning logic)

async def get_current_price(symbol):
    # Fetch from Binance API directly for accuracy
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/fapi/v1/ticker/price?symbol={symbol}"
        async with session.get(url) as resp:
            data = await resp.json()
            return float(data['price'])

async def force_trade(symbol):
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    symbol = symbol.replace('/', '').upper() # Clean input
    
    print(f"--- FORCING SHORT ON {symbol} ---")
    
    # 1. Get Price
    try:
        entry_price = await get_current_price(symbol)
        print(f"Current Price: {entry_price}")
    except Exception as e:
        print(f"Failed to fetch price: {e}")
        return

    # 2. Calculate Params
    # SL: 1.5% above
    sl_price = entry_price * 1.015
    # TP1: 2% below
    tp1_price = entry_price * 0.98
    # TP2: 8% below
    tp2_price = entry_price * 0.92
    
    # Size
    quantity = 0.002 # Hardcoded safety size for now, same as DecisionEngine
    # Logic: Risk 0.5% -> (1000 * 0.005) / (sl - entry)? 
    # DecisionEngine uses fixed 0.002 for now. We stick to that to be safe.

    # 3. Construct Signal
    signal = {
        "symbol": symbol,
        "side": "sell",
        "type": "market",
        "amount": quantity,
        "entry_price": entry_price,
        "params": {
            "stop_loss": sl_price,
            "take_profit_1": tp1_price,
            "take_profit_2": tp2_price
        },
        "scores": {
            "final": 1.0, # Forced High Score
            "pattern": 1.0, 
            "news": 50
        }
    }
    
    print(f"Signal Prepared: {json.dumps(signal, indent=2)}")
    
    confirm = input("Are you sure you want to PUSH this trade? (y/n): ")
    if confirm.lower() == 'y':
        await r.lpush("execution:orders", json.dumps(signal))
        print("✅ Trade Pushed to Execution Queue!")
        # Also log to bot_logs so dashboard sees it
        await r.publish("bot_logs", json.dumps({"type": "info", "message": f"MANUAL OVERRIDE: Shorting {symbol}"}))
    else:
        print("❌ Cancelled.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 force_short.py <SYMBOL>")
    else:
        asyncio.run(force_trade(sys.argv[1]))
