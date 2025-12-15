import os
import asyncio
import json
import websockets
import aiohttp
import pandas as pd
import redis.asyncio as redis
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
DB_PATH = os.getenv("DB_PATH", "exhaustion_bot.db")
# Switching to Mainnet for Scanning (User Request)
BASE_URL = "https://fapi.binance.com"

class MarketCollector:
    def __init__(self):
        self.session = None
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.init_db()

    async def get_session(self):
        if self.session is None:
            # Re-enable Proxy Support (trust_env=True) just in case we need it later.
            # Keeping User-Agent to look like a browser.
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            self.session = aiohttp.ClientSession(trust_env=True, headers=headers)
        return self.session

    def init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS klines (
                symbol TEXT,
                timeframe TEXT,
                timestamp INTEGER,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        ''')
        conn.commit()
        conn.close()

    async def fetch_exchange_info(self):
        session = await self.get_session()
        async with session.get(f"{BASE_URL}/fapi/v1/exchangeInfo") as resp:
            data = await resp.json()
            return data.get('symbols', [])

    async def fetch_ohlcv(self, symbol, timeframe, limit=100):
        # Timeframe map: 1h -> 1h, etc.
        session = await self.get_session()
        params = {
            'symbol': symbol.replace('/', '').replace(':USDT', ''), # Clean symbol
            'interval': timeframe,
            'limit': limit
        }
        try:
            async with session.get(f"{BASE_URL}/fapi/v1/klines", params=params) as resp:
                data = await resp.json()
                
                # ERROR HANDLING: Check if response is an error dict
                if isinstance(data, dict):
                    print(f"Binance Error for {symbol}: {data}")
                    return []
                
                # Check if data is actually a list
                if not isinstance(data, list):
                     print(f"Binance Unexpected Format for {symbol}: {type(data)} -> {data}")
                     return []

                # Parse [t, o, h, l, c, v, ...]
                parsed = []
                for k in data:
                    # Defensive parsing
                    if len(k) < 6: continue 
                    parsed.append([
                        int(k[0]),
                        float(k[1]),
                        float(k[2]),
                        float(k[3]),
                        float(k[4]),
                        float(k[5])
                    ])
                return parsed
        except Exception as e:
            # print(f"Error fetching OHLCV for {symbol} {timeframe}: {e}")
            # Suppress generic noise, focused errors logged above
            pass
            return []

    async def fetch_funding_rate(self, symbol):
        session = await self.get_session()
        params = {'symbol': symbol.replace('/', '').replace(':USDT', '')}
        try:
            async with session.get(f"{BASE_URL}/fapi/v1/premiumIndex", params=params) as resp:
                data = await resp.json()
                # data is dict if symbol param provided
                return float(data.get('lastFundingRate', 0))
        except Exception as e:
            print(f"Error fetching funding for {symbol}: {e}")
            return None

    async def fetch_open_interest(self, symbol):
        session = await self.get_session()
        params = {'symbol': symbol.replace('/', '').replace(':USDT', '')}
        try:
            async with session.get(f"{BASE_URL}/fapi/v1/openInterest", params=params) as resp:
                data = await resp.json()
                return float(data.get('openInterest', 0)) 
                # Note: Testnet might return 'openInterest' (amount) or 'openInterestAmt'??
                # Live docs: openInterest (quantity), openInterestValue (USDT).
                # We want amount.
        except Exception as e:
            print(f"Error fetching OI for {symbol}: {e}")
            return None

    async def save_to_redis(self, symbol, timeframe, data):
        key = f"klines:{symbol}:{timeframe}"
        await self.redis.set(key, json.dumps(data))
    
    # REFACTOR: Use Redis Hash for partial updates (Polling vs Streaming data)
    async def save_metrics_to_redis(self, symbol, funding, oi, price=0.0, change_4h=0.0):
        key = f"metrics:{symbol}"
        # We use HSET so we don't overwrite Price/Change from WebSocket if we are just updating Funding/OI
        mapping = {
            'funding_rate': str(funding),
            'open_interest': str(oi),
            'updated_at': datetime.now().isoformat()
        }
        if price > 0: mapping['price'] = str(price)
        if change_4h != 0: mapping['change_4h'] = str(change_4h)
        
        await self.redis.hset(key, mapping=mapping)
        
        oi_history_key = f"oi_history:{symbol}"
        timestamp = datetime.now().timestamp()
        await self.redis.lpush(oi_history_key, json.dumps({'ts': timestamp, 'oi': oi}))
        await self.redis.ltrim(oi_history_key, 0, 50)

    # NEW: WebSocket Stream for ALL 530+ Coins (Zero API Weight)
    async def listen_ticker_stream(self):
        url = "wss://fstream.binance.com/ws/!ticker@arr"
        print(f"Connecting to Ticker Stream: {url}")
        while True:
            try:
                async with websockets.connect(url) as ws:
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        # Data is list of objects
                        # e.g. [{"s": "BTCUSDT", "c": "95000.00", "P": "5.00" ...}, ...]
                        
                        pipeline = self.redis.pipeline()
                        for t in data:
                            sym = t['s']
                            # Only track USDT perps
                            if not sym.endswith('USDT'): continue
                            
                            price = float(t['c'])
                            change_24h = float(t['P'])
                            
                            key = f"metrics:{sym}"
                            # HSET partial update
                            pipeline.hset(key, mapping={
                                'price': str(price),
                                'change_24h': str(change_24h), # Note: using 24h change for broad market
                                'last_stream_update': datetime.now().isoformat()
                            })
                        
                        await pipeline.execute()
                        # No sleep needed, this is event driven
            except Exception as e:
                print(f"Ticker Stream Error: {e}")
                await asyncio.sleep(5) # Reconnect delay

    # ... (skipping to run)

    async def run(self):
        print("Starting Collector Cycle (Hybrid: WS + Polling)...")
        
        # 1. Start WebSocket Listener (Background)
        asyncio.create_task(self.listen_ticker_stream())
        
        # 2. Continue with Polling (SAFE MODE - Top 20 Only)
        # ... (rest of run method)

    async def save_to_sqlite(self, symbol, timeframe, ohlcv_data):
        def _write():
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            data_to_insert = [
                (symbol, timeframe, candle[0], candle[1], candle[2], candle[3], candle[4], candle[5])
                for candle in ohlcv_data
            ]
            cursor.executemany('''
                INSERT OR REPLACE INTO klines (symbol, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', data_to_insert)
            conn.commit()
            conn.close()
        
        await asyncio.to_thread(_write)

    async def process_symbol(self, symbol):
        # Symbol format from exchangeInfo is clean (e.g. BTCUSDT). 
        # But our system uses 'BTC/USDT' or 'BTC/USDT:USDT'.
        # We need to map properly.
        # Let's say we work with 'BTCUSDT' internally in this func?
        # But we need to save with the key expected by Scanner.
        # Scanner expects: from redis keys "metrics:BTC/USDT" (or keys stored by us).
        
        # If we get symbols from exchangeInfo, they are 'BTCUSDT'.
        # We should store them as 'BTC/USDT' for compatibility?
        # Or simpler: store as 'BTCUSDT' and update scanner to use that?
        # Scanner code: `symbols = [k.split(":")[1] for k in keys]` -> gets 'BTC/USDT' if key is metric:BTC/USDT
        # If we store 'metrics:BTCUSDT', scanner gets 'BTCUSDT'.
        # Scanner `get_klines` uses `klines:BTCUSDT:4h`.
        # This seems cleaner.
        
        clean_symbol = symbol 
        # Wait, run() filters symbols.
        
        timeframes = ['4h', '1h', '15m', '5m']
        
        funding = await self.fetch_funding_rate(clean_symbol)
        oi = await self.fetch_open_interest(clean_symbol)
        
        current_price = 0.0
        change_4h = 0.0

        # Fetch Candles & Calculate Metrics
        for tf in timeframes:
            ohlcv = await self.fetch_ohlcv(clean_symbol, tf)
            if ohlcv:
                await self.save_to_redis(clean_symbol, tf, ohlcv)
                await self.save_to_sqlite(clean_symbol, tf, ohlcv)
                
                # Use 4h data for Price & Change calculation
                if tf == '4h' and len(ohlcv) > 0:
                    latest = ohlcv[-1]
                    # Format: [t, o, h, l, c, v]
                    open_p = float(latest[1])
                    close_p = float(latest[4])
                    current_price = close_p
                    if open_p > 0:
                        change_4h = ((close_p - open_p) / open_p) * 100

        # Save Metrics (Funding, OI, Price, Change)
        if funding is not None and oi is not None:
             await self.save_metrics_to_redis(clean_symbol, funding, oi, current_price, change_4h)

    async def run(self):
        print("Starting Collector Cycle (Hybrid: WS + Polling)...")
        # 1. Start WebSocket Listener (Background)
        asyncio.create_task(self.listen_ticker_stream())

        symbols_info = await self.fetch_exchange_info()
        
        # Filter USDT pairs
        # symbols_info is list of dicts
        target_symbols = []
        for s in symbols_info:
            if s['quoteAsset'] == 'USDT' and s['contractType'] == 'PERPETUAL' and s['status'] == 'TRADING':
                target_symbols.append(s['symbol'])
        
        # Limit 
        if 'BTCUSDT' in target_symbols:
             target_symbols.remove('BTCUSDT')
             
        # Track ALL coins (User Request)
        # final_list = ['BTCUSDT'] + target_symbols
        # print(f"Tracking {len(final_list)} symbols.")
        
        # 2. Hybrid Polling (Smart Mode)
        # We track ALL coins, but only fetch OHLCV (Heavy REST call) if:
        # A) The coin has moved significantly (>3% in 24h/4h) on the WebSocket stream.
        # B) We haven't fetched it in > 60 minutes (Backfill).
        
        print(f"Tracking {len(target_symbols)} symbols (SMART MODE).")
        
        # Concurrency: 5 concurrent workers
        sem = asyncio.Semaphore(5)

        async def protected_process(s):
             async with sem:
                try:
                    # SMART CHECK: Do we need to scan this?
                    # Check Redis metrics populated by WebSocket
                    # If price change is small, we skip REST calls to save weight.
                    
                    key = f"metrics:{s}"
                    m = await self.redis.hgetall(key)
                    
                    should_scan = False
                    reason = "periodic"
                    
                    if not m:
                        # New coin, verify
                        should_scan = True
                        reason = "init"
                    else:
                        # Check last update time
                        updated_at = m.get("updated_at_rest", "2000-01-01T00:00:00")
                        last_ts = datetime.fromisoformat(updated_at).timestamp() if updated_at else 0
                        now_ts = datetime.now().timestamp()
                        
                        # Rule 1: Always scan every 60 mins
                        if (now_ts - last_ts) > 3600: 
                             should_scan = True
                             reason = "stale"
                        
                        # Rule 2: Volatility Trigger (If moved > 3% in 24h)
                        # We use 24h change from WS
                        else:
                            change_24h = abs(float(m.get("change_24h", 0)))
                            # If pumping/dumping, we want fresh candles
                            if change_24h > 3.0: 
                                should_scan = True
                                reason = f"volatility_{change_24h:.1f}%"
                    
                    if should_scan:
                        # print(f"Scanning {s} ({reason})...")
                        await self.process_symbol(s)
                        
                        # Mark as REST updated
                        await self.redis.hset(key, "updated_at_rest", datetime.now().isoformat())
                        
                        # Rate Limit Delay (Weight Safety)
                        await asyncio.sleep(0.5) 
                    
                except Exception as e:
                    # print(f"Error processing {s}: {e}")
                    pass

        # LOOP: Keep checking forever
        while True:
            try:
                # Process Single Cycle
                start_time = datetime.now()
                tasks = [protected_process(s) for s in target_symbols]
                await asyncio.gather(*tasks)
                
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                # print(f"Collector cycle finished in {duration:.1f}s.")
                
                # Check frequency: Every 30 seconds
                # This ensures we catch pumps relatively quickly without hammering Redis/CPU
                await asyncio.sleep(30)

            except Exception as e:
                print(f"Collector Loop Error: {e}")
                await asyncio.sleep(60)

    async def close(self):
        if self.session:
            await self.session.close()

if __name__ == "__main__":
    collector = MarketCollector()
    try:
        asyncio.run(collector.run())
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(collector.close())
