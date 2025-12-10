import os
import asyncio
import json
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
            self.session = aiohttp.ClientSession()
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
                # Parse [t, o, h, l, c, v, ...]
                # CCXT structure: [t, o, h, l, c, v]
                # Binance raw: [t, o, h, l, c, v, ...] (strings)
                parsed = []
                for k in data:
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
            print(f"Error fetching OHLCV for {symbol} {timeframe}: {e}")
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
    
    async def save_metrics_to_redis(self, symbol, funding, oi):
        key = f"metrics:{symbol}"
        data = {
            'funding_rate': funding,
            'open_interest': oi,
            'updated_at': datetime.now().isoformat()
        }
        await self.redis.set(key, json.dumps(data))
        
        oi_history_key = f"oi_history:{symbol}"
        timestamp = datetime.now().timestamp()
        await self.redis.lpush(oi_history_key, json.dumps({'ts': timestamp, 'oi': oi}))
        await self.redis.ltrim(oi_history_key, 0, 50)

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
        
        if funding is not None and oi is not None:
             await self.save_metrics_to_redis(clean_symbol, funding, oi)

        for tf in timeframes:
            ohlcv = await self.fetch_ohlcv(clean_symbol, tf)
            if ohlcv:
                await self.save_to_redis(clean_symbol, tf, ohlcv)
                await self.save_to_sqlite(clean_symbol, tf, ohlcv)

    async def run(self):
        print("Starting Collector Cycle (Raw HTTP)...")
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
        final_list = ['BTCUSDT'] + target_symbols
        print(f"Tracking {len(final_list)} symbols.")
        
        # Concurrency Control to prevent 429 API Ban
        # process_symbol makes ~6 requests. 300 symbols * 6 = 1800 req.
        # Limit to ~5 concurrent symbols => 30 active requests.
        sem = asyncio.Semaphore(5)

        async def protected_process(s):
            async with sem:
                try:
                    await self.process_symbol(s)
                except Exception as e:
                    print(f"Error processing {s}: {e}")

        # Process Single Cycle
        start_time = datetime.now()
        tasks = [protected_process(s) for s in final_list]
        await asyncio.gather(*tasks)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"Collector cycle finished in {duration:.1f}s.")

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
