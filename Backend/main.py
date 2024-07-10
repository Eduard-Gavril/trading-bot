import ta.momentum
from api_testnet import Api_key, Api_secret
from pybit.unified_trading import HTTP
import pandas as pd
import ta
from time import sleep
import time 

# Calc timestamp in milliseconds
current_timestamp_ms = int(round(time.time() * 1000))

session = HTTP(
    api_key=Api_key,
    api_secret=Api_secret,
    testnet=True,
    recv_window=15000,  # adjust the value since we are in a diffrent timezone
)

#ge the info of ure account balance 

def BalanceAccount():
    resp = session.get_wallet_balance(accountType="UNIFIED", coin="USDT")['result']['list'][0]['coin'][0]['walletBalance']
    resp = float(resp)
    return resp


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


#get the symbols if have any position opened, if u dont is gonna return a void array 
#this so u dont open massive position for the same coin 

def get_positions():
    resp =  session.get_positions(
    category ='linear',
    settleCoin = 'USDT'
    )['result']['list']
    pos = []
    for elem in resp:
        pos.append(elem["symbol"])

    return pos



#set different parameter for each coin u trade ( cos for one coin can be goot and bad for another one)

def set_mode(symbol):

    resp = session.switch_margin_mode(
        category = "linear",
        symbol = symbol,
        tradeMode = 1, # 0 for CROSS 1 for ISOLATED
        buyLeverage = 25, # % of leverage
        sellLeverage = 25
    )
    print(resp)

# now we need a funtion to get the decimal number based of the value of the symbol we are trading 
# so we can validate the position we are opening 

def get_precision(symbol):

    resp = session.get_instruments_info(
        category = "linear",
        symbol = symbol
    )["result"]["list"][0]
    
    price = resp["priceFilter"]["tickSize"]
    if '.' in price:
        price = len(price.split('.') [1])
    else:
        price = 0
    qty = resp['lotSizeFilter']['qtyStep']
    if '.' in qty:
        qty = len(qty.split('.') [1])
    else:
        qty = 0


    return price, qty


#print(get_precision("ETHUSDT")) # we should get 2,2


#now we need a funtion to place orders 

def place_order_market(symbol, side):
    price_precision =  get_precision(symbol)[0] #so we get the precisione calculated with the function before 
    qty_precision = get_precision(symbol)[1]

    mark_price = session.get_tickers(
        category = "linear",
        symbol = symbol
    )["result"]["list"][0]["markPrice"]
    mark_price = float(mark_price)
    print(f"Placing {side} order for {symbol}. Mark price: {mark_price}")

    order_qty = round(100/mark_price, qty_precision)  #chenge the value of 100 sice they rapresent the USDT used for operation
    sleep(2)

    if side == "Buy":
        tp_price = round(mark_price + mark_price * 0.02, price_precision) # decimal means 2%
        sl_price = round(mark_price - mark_price * 0.01, price_precision) # decimal means 1%
        resp = session.place_order(
            category = "linear",
            symbol = symbol,
            side = "Buy",
            order_type = "Limit",
            qty = order_qty,
            takeProfit = tp_price,
            stopLoss = sl_price,
            tpTriggerBy='Market',
            slTriggerBy='Market'
        )
    if side == "sell":
            tp_price = round(mark_price - mark_price * 0.02, price_precision) # decimal means 2%
            sl_price = round(mark_price + mark_price * 0.01, price_precision) # decimal means 1%
            resp = session.place_order(
                category = "linear",
                symbol = symbol,
                side = "Sell",
                order_type = "Limit",
                qty = order_qty,
                takeProfit = tp_price,
                stopLoss = sl_price,
                tpTriggerBy='Market',
                slTriggerBy='Market'
            )

    print(resp)


#now we have to define our strategy 

def rsi_signal(symbol):
    kl = klines(symbol)
    rsi = ta.momentum.RSIIndicator(kl.Close).rsi()
    if rsi.iloc[-2] < 30 and rsi.iloc[-1] > 30:
        return "up", round(rsi.iloc[-1], 2)
    if rsi.iloc[-2] > 70 and rsi.iloc[-1] < 70:
        return 'down', round(rsi.iloc[-1], 2)
    else:
        return "none", round(rsi.iloc[-1], 2)
    

max_pos = 50
symbols = get_tickers()

while True:
    balance = BalanceAccount()
    if balance == None:
        print("no more money to trade with")
    if balance != None:
        print(f"Balance: {balance} USD")
        pos = get_positions()
        print(f"You have {len(pos)} positions: {pos}")
        
        if len(pos) <= max_pos:
            for elem in symbols:
                pos = get_positions()
                if len(pos) > max_pos:
                    break
                signal = rsi_signal(elem)
                print(f"the actual signal trand is: {signal}")
                if signal[0] == "none":
                    print("wait for 30sec")
                    sleep(30)
                if signal[0] == 'up' and not elem in pos:
                    print (f'Found BUY signal for {elem}')
                    set_mode(elem)
                    sleep(2)
                    place_order_market(elem, "Buy")
                    sleep(5)
                if signal[0] == 'down' and not elem in pos:
                    print (f'Found SELL signal for {elem}')
                    set_mode(elem)
                    sleep(2)
                    place_order_market(elem, "Sell")
                    sleep(5)
    print("waiting 2 minutes")
    sleep(120)