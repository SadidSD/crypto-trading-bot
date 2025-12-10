import vectorbt as vbt
import numpy as np
import pandas as pd
import ccxt

# simple mock backtest
# In real scenario, would fetch from database or CSV
# Here fetching small sample from CCXT or generating mock data

def run_backtest():
    print("Fetching historical data...")
    # Fetch data (e.g. BTC/USDT 1h)
    symbol = 'BTC/USDT'
    # Need to block for async fetch or use vbt (vbt has wrapper for yfinance/ccxt sometimes, but ccxt is easier manually)
    exchange = ccxt.binance()
    ohlcv = exchange.fetch_ohlcv(symbol, '1h', limit=1000)
    
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df.set_index('time', inplace=True)
    
    print(f"Data loaded: {len(df)} candles.")
    
    # Strategy Logic (Proxy for AI)
    # Pump: Price > 1.05 * Price[4] (5% pump in 4 hours? User said 10-25% in 4H)
    # Let's say we Short if Close > Open * 1.02 (2% up candle) AND Volume > Mean * 2
    
    close = df['close']
    open_p = df['open']
    volume = df['volume']
    
    # Conditions
    pump_cond = close > close.shift(4) * 1.05 # 5% pump in 4h
    vol_cond = volume > volume.rolling(20).mean() * 2
    
    entries = pump_cond & vol_cond
    exits = entries.vbt.signals.fshift(1) # Exit after 1 bar? Or SL/TP?
    
    # vbt.Portfolio.from_signals
    # Using SL/TP
    # SL 1.5%, TP 2% (TP1), TP 5% (TP2)
    # vbt supports SL/TP
    
    pf = vbt.Portfolio.from_signals(
        close, 
        entries, 
        None, # No explicit exit signal, relying on SL/TP
        sl_stop=0.015,
        tp_stop=0.04, # Avg TP
        fees=0.0004, # Binance Futures Taker
        init_cash=1000,
        freq='1h'
    )
    
    print(pf.stats())
    # pf.plot().show() # Would show in browser, but we are headless
    
    # Save stats
    stats = pf.stats()
    stats.to_csv("backtest_results.csv")
    print("Backtest complete. Results saved to backtest_results.csv")

if __name__ == "__main__":
    run_backtest()
