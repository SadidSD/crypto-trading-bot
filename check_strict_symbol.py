import asyncio
import aiohttp
import json

BASE_URL = "https://testnet.binancefuture.com"

async def check_strict():
    print("🔎 Checking strict symbol 'POWERUSDT' on Developer Testnet...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/fapi/v1/exchangeInfo") as resp:
            info = await resp.json()
            symbols = [s['symbol'] for s in info['symbols']]
            
            if 'POWERUSDT' in symbols:
                print("✅ POWERUSDT FOUND on Testnet API.")
                # Get price
                async with session.get(f"{BASE_URL}/fapi/v1/ticker/price?symbol=POWERUSDT") as p_resp:
                    data = await p_resp.json()
                    print(f"💰 Price: {data['price']}")
            else:
                print("❌ POWERUSDT is NOT listed on the Developer Testnet API.")
                print(f"   (Verified against {len(symbols)} available symbols)")
                
            if 'POWRUSDT' in symbols:
                print("ℹ️  POWRUSDT is present (often confused).")

if __name__ == "__main__":
    asyncio.run(check_strict())
