import asyncio
import os
import json
import redis.asyncio as redis
import aiohttp
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# Load env from .env file
load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

async def check_redis():
    print(f"\n--- 1. REDIS CONNECTIVITY ({REDIS_HOST}:{REDIS_PORT}) ---")
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        await r.ping()
        print("✅ Redis Connected Successfully.")
        
        # Check Keys
        metric_keys = await r.keys("metrics:*")
        kline_keys_4h = await r.keys("klines:*:4h")
        kline_keys_1h = await r.keys("klines:*:1h")
        
        print(f"📊 Tracked Symbols (Metrics): {len(metric_keys)}")
        print(f"📊 4H Candle Data Available: {len(kline_keys_4h)}")
        print(f"📊 1H Candle Data Available: {len(kline_keys_1h)}")
        
        if len(kline_keys_1h) < 10:
             print("⚠️ CRITICAL: 1H Data is missing! Scanner needs 1H data to work.")
        
        if len(metric_keys) < 25:
            print("⚠️ NOTE: You are tracking < 25 symbols. This looks like SAFE MODE (Top 20).")
            print("   Large Cap coins (BTC, ETH) rarely pump 10-25% in 4 hours.")
        else:
            print("✅ Broad market tracking detected.")
            
        return r, metric_keys
    except Exception as e:
        print(f"❌ Redis Connection Failed: {e}")
        return None, []

async def analyze_thresholds(r, keys):
    print(f"\n--- 2. SCANNER LOGIC SIMULATION ---")
    print("Checking why no trades are triggering...")
    
    # Current Thresholds (from scanner.py)
    TARGET_PUMP_4H = 10.0 # %
    TARGET_PUMP_1H = 8.0  # %
    
    # Simulation Thresholds
    SIM_PUMP_4H = 2.0  # % (Realistic for Large Caps)
    
    candidates_current = []
    candidates_sim = []
    
    print(f"Sampling keys (debugging data freshness)...")
    
    for k in keys:
        symbol = k.split(":")[1]
        
        # Get Metrics
        try:
            m = await r.hgetall(k)
        except Exception as e:
            if count < 5: print(f"⚠️  Skipping {k}: {e} (Likely old string key)")
            continue
            
        if not m: continue
        
        # Get Klines (needed for pump calc)
        target_key = f"klines:{symbol}:1h"
        k_data = await r.get(target_key)
        
        if count == 0:
             print(f"🔍 DEBUG RAW KEY: {target_key}")
             if not k_data: print("   -> Key NOT FOUND")
             else: print(f"   -> Data Length: {len(json.loads(k_data))} candles")
        
        if not k_data: continue
        
        klines = json.loads(k_data)
        if len(klines) < 5: 
            if count == 0: print(f"   -> SKIPPING: Too few candles ({len(klines)})")
            continue
        
        df = pd.DataFrame(klines, columns=['t','o','h','l','c','v'])
        
        # DEBUG: Check Freshness of first few
        if count < 3:
            last_ts = int(df.iloc[-1]['t'])
            last_time = datetime.fromtimestamp(last_ts / 1000).isoformat()
            print(f"🔍 DEBUG {symbol}: Latest Candle Time: {last_time} | Price: {df.iloc[-1]['c']}")
            count += 1
        
        # Calc Pump
        price_now = float(df.iloc[-1]['c'])
        price_4h_ago = float(df.iloc[-4]['o']) # Approx
        
        if price_4h_ago == 0: continue
        
        pump_4h = (price_now - price_4h_ago) / price_4h_ago * 100
        
        # Check Matches
        if pump_4h >= TARGET_PUMP_4H:
            candidates_current.append((symbol, pump_4h))
        
        if pump_4h >= SIM_PUMP_4H:
            candidates_sim.append((symbol, pump_4h))
            
    print(f"\nRESULTS:")
    print(f"🔹 Matches with CURRENT Thresholds (> {TARGET_PUMP_4H}%): {len(candidates_current)}")
    for c in candidates_current: print(f"   - {c[0]}: {c[1]:.2f}%")
    
    print(f"🔸 Matches with SIMULATED Thresholds (> {SIM_PUMP_4H}%): {len(candidates_sim)}")
    if candidates_sim:
        print(f"   (Logic is working! But your thresholds are too high for {len(keys)} large cap coins.)")
        print("   Samples:")
        for c in candidates_sim[:3]: print(f"   - {c[0]}: {c[1]:.2f}%")
    else:
        print("   (Even with 2% thresholds, nothing found. Market might be very flat.)")

async def check_binance_execution():
    print(f"\n--- 3. BINANCE EXECUTION API ---")
    if not BINANCE_API_KEY:
        print("❌ BINANCE_API_KEY not found in .env")
        return
        
    import hmac
    import hashlib
    import time
    
    try:
        # Executor uses Testnet
        base_url = "https://testnet.binancefuture.com"
        
        async with aiohttp.ClientSession() as session:
            # 1. Sync Time
            try:
                async with session.get(f"{base_url}/fapi/v1/time") as t_resp:
                    t_data = await t_resp.json()
                    server_time = int(t_data['serverTime'])
                    local_time = int(time.time() * 1000)
                    offset = server_time - local_time
                    print(f"🕒 Time Sync: Local={local_time}, Server={server_time}, Offset={offset}ms")
            except Exception as e:
                print(f"⚠️ Time Sync Failed: {e}. Using local time.")
                offset = 0

            # 2. Check Account (Signed)
            url = f"{base_url}/fapi/v2/account"
            
            # Use Server Time
            timestamp = int(time.time() * 1000) + offset
            params = {'timestamp': timestamp, 'recvWindow': 10000} # Increased recvWindow
            query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
            signature = hmac.new(
                BINANCE_SECRET_KEY.encode('utf-8'), 
                query_string.encode('utf-8'), 
                hashlib.sha256
            ).hexdigest()
            
            full_url = f"{url}?{query_string}&signature={signature}"
            headers = {"X-MBX-APIKEY": BINANCE_API_KEY}
            
            async with session.get(full_url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    balance = float(data.get('availableBalance', 0))
                    
                    print(f"✅ API Connection: OK")
                    print(f"💰 Testnet Futures Balance: {balance:.2f} USDT")
                    
                    if balance < 10:
                        print("⚠️ Low Balance! Bot might fail to place orders.")
                else:
                    text = await resp.text()
                    print(f"❌ API Error {resp.status}: {text}")
    except Exception as e:
        print(f"❌ API Exception: {e}")

async def main():
    print("=== EXHAUSTION BOT DIAGNOSTIC TOOL ===")
    r, keys = await check_redis()
    if r and keys:
        await analyze_thresholds(r, keys)
        await r.close()
    
    await check_binance_execution()
    print("\n=== DIAGNOSIS COMPLETE ===")

if __name__ == "__main__":
    asyncio.run(main())
