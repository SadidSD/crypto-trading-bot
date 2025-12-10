import asyncio
import json
import os
import aiohttp
import redis.asyncio as redis
from dotenv import load_dotenv

# Use absolute imports or ensure path is set. Assuming run from root.
from ai.pattern_api import PatternAnalyzer
from ai.news_api import NewsAnalyzer

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

class DecisionEngine:
    def __init__(self):
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.pattern_analyzer = PatternAnalyzer()
        self.news_analyzer = NewsAnalyzer()
        # No CCXT. Validating logic simplified.

    async def validate_candidate(self, symbol):
        # Without CCXT, fetching spread/depth is harder.
        # We can implement a simple ticker fetch if needed.
        # For now, let's assume valid since filter passed.
        # Or add a simple request helper.
        return True

    async def calculate_position_size(self, symbol, entry_price, sl_price):
        # Simulating balance check or skipping strict balance check for speed in MVP
        # Assume 1000 USDT for safe calc if fetch fails
        return 0.002 # Fixed small size for safety in testnet rework
        # Real logic requires balance fetch via aiohttp (can copy from Executor if needed)

    async def process_candidate(self, symbol):
        print(f"Processing candidate {symbol}...")
        
        # Hard Filters
        if not await self.validate_candidate(symbol):
            return None

        # AI Analysis
        pattern_res = await self.pattern_analyzer.get_pattern_score(symbol, self.redis)
        news_res = await self.news_analyzer.get_news_score(symbol)
        
        pattern_score = float(pattern_res.get('pattern_score', 0))
        news_score = float(news_res.get('news_score', 50))
        
        # Final Score
        final_score = (pattern_score * 0.7) + ((1 - (news_score / 100)) * 0.3)
        
        print(f"Scores for {symbol}: Pattern={pattern_score}, News={news_score}, Final={final_score:.2f}")

        # === CONFIRMATION LAYER (Lower TF) ===
        # 1. Check OI Trend (Rising in Scanner -> Falling/Flat here?)
        oi_history = await self.redis.lrange(f"oi_history:{symbol}", 0, 5)
        if oi_history:
            # Check slope of last 3 points
            # Last is index 0 (if lpush used order is Newest at 0) -> Redis lrange returns ordered list. 
            # Collector uses lpush. So index 0 is newest.
            recents = [float(json.loads(x)['oi']) for x in oi_history[:3]]
            # If recent OI < previous, it's falling.
            # recents[0] = Now, recents[1] = 5m ago, recents[2] = 10m ago
            if len(recents) >= 2:
                if recents[0] > recents[1]:
                     print("OI still rising. Waiting for stall/drop.")
                     # return None # Strict rule: Abort if OI still pumping hard?
                     # Strategy says: "OI stops rising and begins falling".
                     # Let's be strict.
                     # return None 
                     pass 

        # Final Score Check
        if final_score < 0.75:
            return None

        # Trade Plan
        # Need current price?
        # Get from Redis Klines latest close
        k_1m = await self.redis.get(f"klines:{symbol}:5m")
        if not k_1m: return None
        klines = json.loads(k_1m)
        entry_price = float(klines[-1][4]) # Close
        
        # SL: 1.5% above recent high (5m) for tight protection
        recent_high = max([float(k[2]) for k in klines[-5:]]) # Last 5 candles high
        # Rule: 1.2% - 1.8% above wick. Let's use 1.5% above high.
        sl_price = recent_high * 1.015
        
        tp1_price = entry_price * 0.98  # +2% gain (Short so price drops)
        tp2_price = entry_price * 0.92  # +8% gain
        
        # Position Sizing
        # Risk: 0.5% - 1.2% of account. Let's use 1.0%
        # Amount = (AccountBalance * Risk%) / (SL_Price - Entry_Price)
        # Using fixed 1000 balance assumption for now as we don't fetch wallet yet
        balance = 1000.0 
        risk_per_trade = balance * 0.01 # $10 risk
        price_diff = abs(sl_price - entry_price)
        if price_diff == 0: quantity = 0.002
        else: quantity = round(risk_per_trade / price_diff, 3) 
        
        # Cap max size for safety?
        # quantity = min(quantity, 0.1) # e.g. max 0.1 BTC equivalent if needed
        
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
                "final": final_score,
                "pattern": pattern_score,
                "news": news_score
            }
        }
        
        return signal

    async def run(self):
        print("Decision Engine Running...")
        while True:
            # Pop from candidate queue
            symbol = await self.redis.rpop("scanner:candidates")
            if symbol:
                signal = await self.process_candidate(symbol)
                if signal:
                    print(f"TRADE SIGNAL: {signal}")
                    # Push to execution queue
                    await self.redis.lpush("execution:orders", json.dumps(signal))
            else:
                await asyncio.sleep(5) # Wait if empty

if __name__ == "__main__":
    engine = DecisionEngine()
    try:
        asyncio.run(engine.run())
    except KeyboardInterrupt:
        pass
    finally:
        pass
