from api_testnet import Api_key, Api_secret
from pybit.unified_trading import HTTP
import pandas as pd
import ta
from time import sleep
import time 

# Calcola il timestamp corrente in millisecondi
current_timestamp_ms = int(round(time.time() * 1000))

session = HTTP(
    api_key=Api_key,
    api_secret=Api_secret,
    testnet=True,
    recv_window=15000,  # adjust the value since we are in a diffrent timezone
)

def BalanceAccount():
    resp = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")['result']['list'][0]['coin'][0]['walletBalance']
    resp = float(resp)
    return resp

print (f'Your balance: {BalanceAccount()} USDT')


#function to get all the coins tradable 
def get_tickers():
    
    resp = session.get_tickers (category="linear")['result']['list']
    symbols = []
    for elem in resp:
        if 'USDT' in elem['symbol'] and not 'USDC' in elem['symbol']:
            symbols.append(elem['symbol'])
    return symbols



#funtion to get de candles of X coin 
def klines (symbol):
    resp = session.get_kline(
        category='linear',
        symbol=symbol,
        interval=15, #minutes
        limit=500 #last 500 candles
        )['result']['list']
    resp = pd.DataFrame(resp)
    resp.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Turnover']
    resp = resp.set_index('Time')
    resp = resp.astype(float)
    resp = resp[::-1]
    return resp
print (klines ('ETHUSDT'))



