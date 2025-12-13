import asyncio
import json
import os
import time
import hmac
import hashlib
import aiohttp
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

# Executor uses TESTNET keys for safety
BINANCE_API_KEY = os.getenv("BINANCE_TESTNET_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_TESTNET_SECRET_KEY")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Switching to Testnet for Execution
BASE_URL = "https://testnet.binancefuture.com"

# --- SAFETY LOCK ---
# User requested "Enable trading".
DRY_RUN = False
# -------------------

class TradeExecutor:
    def __init__(self):
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        self.session = None

    async def get_session(self):
        if self.session is None:
            # trust_env=True enables reading HTTP_PROXY/HTTPS_PROXY from environment
            self.session = aiohttp.ClientSession(trust_env=True)
        return self.session

    def get_signature(self, params):
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return hmac.new(BINANCE_SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

    async def notify(self, message):
        print(f"NOTIFICATION: {message}")
        try:
             await self.redis.lpush("notifications", message)
             # Also push to 'bot_logs' list and publish to 'bot_logs' channel for WS
             log_entry = json.dumps({"timestamp": time.time(), "message": message, "type": "info"})
             await self.redis.lpush("bot_logs", log_entry)
             await self.redis.ltrim("bot_logs", 0, 99)
             await self.redis.publish("bot_logs", log_entry)
        except Exception as e:
             print(f"Failed to push notification: {e}")

    async def send_request(self, method, endpoint, params=None):
        session = await self.get_session()
        url = BASE_URL + endpoint
        
        if params is None: params = {}
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 5000
        params['signature'] = self.get_signature(params)
        
        headers = {'X-MBX-APIKEY': BINANCE_API_KEY}
        
        async with session.request(method, url, params=params, headers=headers) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise Exception(f"API Error {resp.status}: {data}")
            return data

    async def execute_trade(self, signal):
        symbol = signal['symbol'].replace('/', '') # BTC/USDT -> BTCUSDT
        side = signal['side'].upper()
        amount = float(signal['amount'])
        params = signal['params']
        sl_price = float(params['stop_loss'])
        tp1 = float(params['take_profit_1'])
        tp2 = float(params['take_profit_2'])

        print(f"Executing trade for {symbol}, Size: {amount}...")

        try:
            # 1. Place Market Entry
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': amount,
            }
            
            if DRY_RUN:
                print(f"[DRY RUN] Would have placed ENTRY {side} for {amount} {symbol}")
                order = {'orderId': 'SIMULATED_ENTRY'}
            else:
                order = await self.send_request('POST', '/fapi/v1/order', order_params)
                print(f"Entry Order Placed: {order['orderId']}")
            
            # 2. Place Stop Loss (STOP_MARKET)
            sl_side = 'BUY' if side == 'SELL' else 'SELL'
            sl_params = {
                'symbol': symbol,
                'side': sl_side,
                'type': 'STOP_MARKET',
                'stopPrice': sl_price,
                'closePosition': 'true' # Reduce only for SL usually means closePosition
                # Or use quantity+reduceOnly. For simplicity using closePosition=true which closes everything? 
                # Better: Use quantity.
            }
            # Note: closePosition=true ignores quantity.
            # Let's use quantity with reduceOnly
            sl_params = {
                'symbol': symbol,
                'side': sl_side,
                'type': 'STOP_MARKET',
                'stopPrice': sl_price,
                'quantity': amount,
                'reduceOnly': 'true'
            }
            
            if DRY_RUN:
                 print(f"[DRY RUN] Would have placed SL at {sl_price}")
                 sl_order = {'orderId': 'SIMULATED_SL'}
            else:
                sl_order = await self.send_request('POST', '/fapi/v1/order', sl_params)
                print(f"SL Placed: {sl_order['orderId']}")

            # 3. Place Take Profits (LIMIT)
            tp_qty = round(amount / 2, 3) # Be careful with precision!
            # For now, simplistic rounding.
            
            tp1_params = {
                'symbol': symbol,
                'side': sl_side,
                'type': 'LIMIT',
                'price': tp1,
                'quantity': tp_qty,
                'timeInForce': 'GTC',
                'reduceOnly': 'true'
            }
            if DRY_RUN:
                 print(f"[DRY RUN] Would have placed TP1 at {tp1}")
                 tp1_order = {'orderId': 'SIMULATED_TP1'}
            else:
                tp1_order = await self.send_request('POST', '/fapi/v1/order', tp1_params)
                print(f"TP1 Placed: {tp1_order['orderId']}")
            
            tp2_params = {
                'symbol': symbol,
                'side': sl_side,
                'type': 'LIMIT',
                'price': tp2,
                'quantity': tp_qty, # Remainder
                'timeInForce': 'GTC',
                'reduceOnly': 'true'
            }
            if DRY_RUN:
                 print(f"[DRY RUN] Would have placed TP2 at {tp2}")
                 tp2_order = {'orderId': 'SIMULATED_TP2'}
            else:
                tp2_order = await self.send_request('POST', '/fapi/v1/order', tp2_params)
                print(f"TP2 Placed: {tp2_order['orderId']}")
            
            trade_event = {
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "entry_price": signal.get('entry_price', 0), # Ensure this is passed
                "timestamp": time.time(),
                "status": "dry_run" if DRY_RUN else "executed",
                "sl": sl_price,
                "tp1": tp1,
                "tp2": tp2,
                "scores": signal.get('scores', {})
            }
            
            # Persist to history for Dashboard
            await self.redis.lpush("trade_history", json.dumps(trade_event))
            # Keep last 1000
            await self.redis.ltrim("trade_history", 0, 999)
            
            await self.notify(f"Executed Short {symbol}\nSL: {sl_price}\nTP1: {tp1}\nTP2: {tp2}")

        except Exception as e:
            print(f"Execution Error {symbol}: {e}")
            await self.notify(f"Execution Failed for {symbol}: {e}")

    async def run(self):
        print("Executor Engine Running (Raw HTTP)...")
        while True:
            item = await self.redis.rpop("execution:orders")
            if item:
                signal = json.loads(item)
                await self.execute_trade(signal)
            else:
                await asyncio.sleep(1)
            
    async def close(self):
         if self.session:
             await self.session.close()

if __name__ == "__main__":
    executor = TradeExecutor()
    try:
        asyncio.run(executor.run())
    except KeyboardInterrupt:
        pass
    finally:
        asyncio.run(executor.close())
