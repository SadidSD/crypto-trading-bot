import os
import asyncio
import json
import redis.asyncio as redis
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

class MarketScanner:
    def __init__(self):
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    async def get_klines(self, symbol, timeframe):
        key = f"klines:{symbol}:{timeframe}"
        data = await self.redis.get(key)
        if not data:
            return None
        return json.loads(data)

    async def get_metrics(self, symbol):
        key = f"metrics:{symbol}"
        data = await self.redis.hgetall(key)
        if not data:
            return None
        return data # Already a dict, no need to json.loads

    async def get_oi_history(self, symbol):
        key = f"oi_history:{symbol}"
        data = await self.redis.lrange(key, 0, 5) # Get recent history
        if not data:
            return []
        return [json.loads(x) for x in data]

    def check_pump(self, df_4h, df_1h):
        if df_4h.empty or df_1h.empty:
            return False, 0, 0

        # Current price
        current_price = df_4h.iloc[-1]['close'] # Assuming close of last closed candle or current, depends on data
        # Actually latest kline might be open. If collector fetches limit 100, last one is latest.
        
        # 4H pump: (High - Low_of_start) / Low_of_start? Or just Open vs Close?
        # User: "pump 10-25% in 4H". This usually means current price vs price 4H ago.
        # But 4H klines: 1 candle is 4H.
        # Let's check the last closed 4H candle, or current if live?
        # Safe bet: comparison over a minimal window.
        # Let's say % change in the last candle or rolling 2.
        
        # Simpler: (Current - Open of 4h AGO) / Open of 4h AGO
        # With 4H timeframe, looking at the last completed candle + current partial?
        # Let's look at the % diff between current price and Open of the candle 4 hours ago (which is 2 candles ago if using 4H TF?)
        # Let's simplify: look at the % change of the last *completed* 4H candle or the current candle if it's running?
        # "pump 10-25% in 4H" -> Usually means the price rose that much in that timeframe.
        # I'll compare Current Price vs Open of the candle at index -2 (previous) or similar.
        # Actually, using 1H candles is more granular for a "4H pump".
        # Let's use 1H candles for the 4H measurement to be precise.
        # Last 4 1H candles.
        
        if len(df_1h) < 5:
            return False, 0, 0
            
        price_now = df_1h.iloc[-1]['close']
        price_4h_ago = df_1h.iloc[-4]['open']
        price_1h_ago = df_1h.iloc[-1]['open'] # Last 1H candle start

        pct_4h = (price_now - price_4h_ago) / price_4h_ago * 100
        pct_1h = (price_now - price_1h_ago) / price_1h_ago * 100
        
        return True, pct_4h, pct_1h

    def check_volume_spike(self, df_1h):
        # Volume spike >= 3x last 20 candles average
        if len(df_1h) < 21:
            return False
        
        current_vol = df_1h.iloc[-1]['volume']
        avg_vol = df_1h.iloc[-21:-1]['volume'].mean() # Average of previous 20, excluding current?
        # Or if -1 is current partial, maybe -2 is better?
        # Assuming -1 is the "spike" candle we are interested in.
        
        if avg_vol == 0: return False
        return current_vol >= 3 * avg_vol

    async def check_btc_trend(self):
        # Fetch BTC 15m data
        k = await self.redis.get("klines:BTC/USDT:USDT:15m")
        if not k:
            # Try without :USDT suffix if logic differs, but collector uses consistent naming
            k = await self.redis.get("klines:BTC/USDT:15m")
        
        if not k: return False # Assume not bullish (safe to short) or True (unsafe)? 
        # If no data, maybe safe to skip filter or block? Let's default to allowing trades but warning.
        # Actually safer to block? User said "BTC 15m not strongly bullish".
        # If we can't see BTC, we assume neutral.
        
        data = json.loads(k)
        df = pd.DataFrame(data, columns=['time','open','high','low','close','volume'])
        
        if len(df) < 5: return False
        
        # Check if strongly bullish:
        # 1. Last candle > 1% move?
        last_open = df.iloc[-1]['open']
        last_close = df.iloc[-1]['close']
        change_pct = (last_close - last_open) / last_open * 100
        
        # 2. RSI check (simple manual calc or pandas)
        # Simple momentum: close > SMA20 by 1%?
        # Let's use simple % change for "Strongly Bullish"
        
        is_strongly_bullish = change_pct > 1.0 # 1% green candle in 15m is strong
        
        return is_strongly_bullish

    def calculate_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    async def scan(self):
        print("Starting Scan...")
        keys = await self.redis.keys("metrics:*")
        symbols = [k.split(":")[1] for k in keys]
        
        candidates = []

        # Check BTC Trend
        # We want "Not Strongly Bullish". So if check_btc returns True (Bullish), we skip scan.
        btc_bullish = await self.check_btc_trend()
        if btc_bullish:
            print("BTC is strongly bullish. Skipping scan for shorts.")
            return

        for symbol in symbols:
            # Yield control to Event Loop (Prevents unresponsiveness/502s)
            await asyncio.sleep(0)
            
            # Skip if symbol is BTC
            if "BTC" in symbol and len(symbol) < 9: continue # Simple skip for BTC pairs if needed
            
            # Fetch data
            klines_4h_raw = await self.get_klines(symbol, '4h')
            klines_1h_raw = await self.get_klines(symbol, '1h')
            metrics = await self.get_metrics(symbol)
            oi_history = await self.get_oi_history(symbol)

            if not klines_4h_raw or not klines_1h_raw or not metrics:
                continue

            df_4h = pd.DataFrame(klines_4h_raw, columns=['time','open','high','low','close','volume'])
            df_1h = pd.DataFrame(klines_1h_raw, columns=['time','open','high','low','close','volume'])

            # Filters
            has_data, pump_4h, pump_1h = self.check_pump(df_4h, df_1h)
            
            if not has_data: continue
            
            # 1. Pump Conditions (Updated Strategy)
            # 4H: 10-25%
            if not (10 <= pump_4h <= 25): continue
            
            # 1H: 8-15% (Re-enabled per V2 Strategy)
            if not (8 <= pump_1h <= 15): continue
            
            # 2. Volume Spike
            if not self.check_volume_spike(df_1h): continue
            
            # 2b. RSI Overextension (New)
            # Need series of closes
            rsi_series = self.calculate_rsi(df_1h['close'], 14)
            current_rsi = rsi_series.iloc[-1]
            if current_rsi < 70: continue # Must be overextended

            # 3. Funding Positive (implies long bias we want to short)
            if float(metrics['funding_rate']) <= 0: continue
            
            # 4. OI Increase >= 10%
            # Compare current OI to oldest in our short history (implied ~1h+ ago if collector runs frequently)
            current_oi = float(metrics['open_interest'])
            # Finds oldest OI in the history list we kept
            if not oi_history: continue
            oldest_oi_entry = oi_history[-1] # List is pushed left, so last is oldest
            oldest_oi = float(oldest_oi_entry['oi'])
            
            if oldest_oi == 0: continue
            oi_increase = (current_oi - oldest_oi) / oldest_oi * 100
            
            if oi_increase < 10: continue

            print(f"Candidate found: {symbol} (4H: {pump_4h:.1f}%, 1H: {pump_1h:.1f}%)")
            candidates.append(symbol)
            
            # --- DATA SHEET LOGGING (User Request) ---
            from datetime import datetime
            log_file = "candidates_log.csv"
            timestamp = datetime.now().isoformat()
            
            # Create header if not exists
            if not os.path.exists(log_file):
                with open(log_file, "w") as f:
                    f.write("Timestamp,Symbol,Price,Pump_4h,Pump_1h,Volume,Funding,OI_Increase\n")
            
            # Append entry
            with open(log_file, "a") as f:
                f.write(f"{timestamp},{symbol},{price_now},{pump_4h:.2f},{pump_1h:.2f},{df_1h.iloc[-1]['volume']},{metrics['funding_rate']},{oi_increase:.2f}\n")
            # -----------------------------------------

        # Push to Queue
        if candidates:
            await self.redis.lpush("scanner:candidates", *candidates)
            print(f"Pushed {len(candidates)} candidates to queue.")

if __name__ == "__main__":
    scanner = MarketScanner()
    asyncio.run(scanner.scan())
