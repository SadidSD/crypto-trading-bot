import asyncio
import os
import json
import redis.asyncio as redis
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

async def debug_luna():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    symbol = "BOBUSDT" 

    print(f"--- Debugging {symbol} ---")
    
    # 1. Get Data
    # Keys might be klines:LUNA2USDT:4h or klines:LUNA2/USDT:4h
    # Scanner usually strips / for keys? 
    # check_market_movements.py used keys = r.keys("klines:*:4h") and split :
    
    # Let's try both
    k4 = await r.get(f"klines:{symbol}:4h")
    if not k4:
        symbol_alt = "LUNA2/USDT"
        k4 = await r.get(f"klines:{symbol_alt}:4h")
        if k4:
            symbol = symbol_alt
            
    if not k4:
        print("❌ No 4H Data found in Redis.")
        return

    k1 = await r.get(f"klines:{symbol}:1h")
    metrics = await r.get(f"metrics:{symbol}")
    # oi_hist_ invalid = False # Placeholder (Removed typo)
    
    if not k1 or not metrics:
        print("❌ Missing 1H data or Metrics.")
        return

    data_4h = json.loads(k4)
    data_1h = json.loads(k1)
    metrics_data = json.loads(metrics)
    
    # 2. Check 4H Pump
    # Scanner logic: (close_now - open_now) / open_now? 
    # Wait, my previous manual check in debug_scanner.py was:
    # change_4h = ((curr_close - curr_open) / curr_open) * 100
    # Scanner.check_pump uses:
    # pct_4h = (price_now - price_4h_ago) / price_4h_ago * 100
    # where price_4h_ago = df_1h.iloc[-4]['open']
    
    # Let's replicate Scanner logic EXACTLY
    df_1h = pd.DataFrame(data_1h, columns=['time','open','high','low','close','volume'])
    
    if len(df_1h) < 5:
        print("❌ Not enough 1H data.")
        return

    price_now = float(df_1h.iloc[-1]['close'])
    price_4h_ago = float(df_1h.iloc[-4]['open'])
    
    pump_4h = (price_now - price_4h_ago) / price_4h_ago * 100
    print(f"4H Pump: {pump_4h:.2f}% (Threshold: 10-25%)")
    
    # 3. Check Volume Spike
    current_vol = float(df_1h.iloc[-1]['volume'])
    avg_vol = df_1h.iloc[-21:-1]['volume'].mean()
    vol_multiple = current_vol / avg_vol if avg_vol > 0 else 0
    print(f"Volume Spike: {vol_multiple:.2f}x (Threshold: >3x)")
    
    # 4. Check Funding
    funding = float(metrics_data.get('funding_rate', 0))
    print(f"Funding: {funding:.6f} (Threshold: >0)")
    
    # 5. Check OI
    # Need to fetch OI history list
    oi_key = f"oi_history:{symbol}"
    oi_hist_list = await r.lrange(oi_key, 0, 50)
    current_oi = float(metrics_data.get('open_interest', 0))
    
    oi_pct = 0
    if oi_hist_list:
        oldest = json.loads(oi_hist_list[-1])
        oldest_oi = float(oldest['oi'])
        if oldest_oi > 0:
            oi_pct = (current_oi - oldest_oi) / oldest_oi * 100
    
    print(f"OI Increase: {oi_pct:.2f}% (Threshold: >10%)")
    
    # Conclusion
    reasons = []
    if not (10 <= pump_4h <= 25): reasons.append("4H Pump")
    if not (vol_multiple > 3): reasons.append("Volume")
    if not (funding > 0): reasons.append("Funding")
    if not (oi_pct > 10): reasons.append("OI")
    
    if not reasons:
        print("✅ YES! It is a candidate.")
    else:
        print(f"❌ NO. Failed: {', '.join(reasons)}")

if __name__ == "__main__":
    asyncio.run(debug_luna())
