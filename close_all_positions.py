import asyncio
import os
import time
import hmac
import hashlib
import aiohttp
from dotenv import load_dotenv

load_dotenv()

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
BASE_URL = "https://testnet.binancefuture.com"

class PositionCloser:
    def __init__(self):
        self.session = None

    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    def get_signature(self, params):
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return hmac.new(BINANCE_SECRET_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

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
                print(f"Error {resp.status} on {endpoint}: {data}")
                return None
            return data

    async def close_all(self):
        print("Fetching Open Positions...")
        positions = await self.send_request('GET', '/fapi/v2/positionRisk')
        
        if not positions:
            print("No positions found or error fetching.")
            return

        active_positions = [p for p in positions if float(p['positionAmt']) != 0]
        
        if not active_positions:
            print("No active positions to close.")
            
            # Check for open orders anyway?
            # Let's clean up open orders for checked symbols or all symbols?
            # Harder to know all symbols with open orders without looking.
            # But usually we only trade a few.
            return

        for p in active_positions:
            symbol = p['symbol']
            amt = float(p['positionAmt'])
            side = 'SELL' if amt > 0 else 'BUY'
            qty = abs(amt)
            
            print(f"Closing {symbol}: {amt} -> {side} Market Order")
            
            # Close Position
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': qty,
                'reduceOnly': 'true'
            }
            res = await self.send_request('POST', '/fapi/v1/order', order_params)
            if res:
                print(f"Closed {symbol}. OrderID: {res.get('orderId')}")
            
            # Cancel All Open Orders (SL/TP)
            print(f"Cancelling open orders for {symbol}...")
            cancel_params = {'symbol': symbol}
            await self.send_request('DELETE', '/fapi/v1/allOpenOrders', cancel_params)
            print("Orders canceled.")

    async def close_session(self):
        if self.session:
            await self.session.close()

if __name__ == "__main__":
    closer = PositionCloser()
    try:
        asyncio.run(closer.close_all())
    finally:
        asyncio.run(closer.close_session())
