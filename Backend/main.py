import ta.momentum, ta.trend, ta.volatility
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
        if 'USDT' in elem['symbol'] and not 'USDC' in elem['symbol'] and not "1" in elem['symbol'] :
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
    df = pd.DataFrame(resp)
    if df.empty:  # check if the dataframe is empty 
        print(f"No data available for {symbol}")
        return pd.DataFrame()  # if so u get a void db 
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
    try:
        resp = session.switch_margin_mode(
            category='linear',
            symbol=symbol,
            tradeMode=1,
            buyLeverage=25,
            sellLeverage=25
        )
        print("mode set ... OK")
    except Exception as err:
        print(f"mode set ... NOK")

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

#now we need a funtion to place orders 

def place_order_market(symbol, side):
    price_precision =  get_precision(symbol)[0] #so we get the precisione calculated with the function before 
    qty_precision = get_precision(symbol)[1]

    mark_price = session.get_tickers(
        category = "linear",
        symbol = symbol
    )["result"]["list"][0]["markPrice"]
    mark_price = float(mark_price)
    print(f"Trying placing {side} order for {symbol}")

    order_qty = round(100/mark_price, qty_precision)  #chenge the value of 100 sice they rapresent the USDT used for operation
    sleep(2)

    #definition of  entry price point
    entry_price = mark_price  
    print(f"Entry price for {symbol}: {entry_price}")

    #define resp before existing 
    resp = {"error": True, "message": "Order not placed"}

    if side == "Buy":
        tp_price = round(mark_price + mark_price * 0.02, price_precision) # decimal means 2%
        sl_price = round(mark_price - mark_price * 0.01, price_precision) # decimal means 1%
        try:
            resp = session.place_order(
                category = "linear",
                symbol = symbol,
                side = "Buy",
                order_type = "Limit",
                qty = order_qty,
                price=str(entry_price),  # entry price point
                takeProfit = tp_price,
                stopLoss = sl_price,
                tpTriggerBy=None, #removed or set for market operations 
                slTriggerBy=None  #removed or set for market operations 
            )
        except Exception as e:
            print(f"Error creating order, NOK")
    if side == "sell":
            tp_price = round(mark_price - mark_price * 0.02, price_precision) # decimal means 2%
            sl_price = round(mark_price + mark_price * 0.01, price_precision) # decimal means 1%
            try:
                resp = session.place_order(
                    category = "linear",
                    symbol = symbol,
                    side = "Sell",
                    order_type = "Limit",
                    qty = order_qty,
                    price=str(entry_price),  # entry price point
                    takeProfit = tp_price,
                    stopLoss = sl_price,
                    tpTriggerBy=None, #removed or set for market operations 
                    slTriggerBy=None  #removed or set for market operations 
                )
            except Exception as e:
                        print(f"Error creating order, NOK")
    print(resp)
    return resp

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


def adx_signal(symbol):
    # get stick
    kl = klines(symbol)

    # Calc ADX trend
    adx_indicator = ta.trend.ADXIndicator(kl['High'], kl['Low'], kl['Close'])
    adx = adx_indicator.adx()
    adx_plus = adx_indicator.adx_pos()
    adx_minus = adx_indicator.adx_neg()

    adx_val_old = adx.iloc[-2]
    adx_val = adx.iloc[-1]
    adx_plus_val = adx_plus.iloc[-1]
    adx_minus_val = adx_minus.iloc[-1]

    #bull
    if adx_plus_val > adx_minus_val and adx_val > adx_val_old:
        #print(f"AD+: {round(adx_plus_val,2)} AD-: {round(adx_minus_val,2)} is Trend UP with: {round(adx_val-adx_val_old,2)}")
        return "up"
    #bear
    if adx_minus_val > adx_plus_val and adx_val > adx_val_old:
        #print(f"AD+: {round(adx_plus_val,2)} AD-: {round(adx_minus_val,2)} is Trend DOWN with: {round(adx_val-adx_val_old,2)}")
        return "down"
 
def BB_signal(symbol):
    # get stick
    kl = klines(symbol)

    bb_indicator_H = ta.volatility.bollinger_hband(kl.Close, window=15, window_dev=1.5)
    bb_indicator_L = ta.volatility.bollinger_lband(kl.Close, window=15, window_dev=1.5)
    bb_indicator_MA = ta.volatility.bollinger_mavg(kl.Close, window=15)

    bb_indicator_H_value = round(bb_indicator_H.iloc[-1])
    bb_indicator_L_value = round(bb_indicator_L.iloc[-1])
    bb_indicator_MA_value = round(bb_indicator_MA.iloc[-1])


    return bb_indicator_H_value , bb_indicator_L_value , bb_indicator_MA_value


print(f"BB: {BB_signal('ETHUSDT')}")

def EMA_signal(symbol):
    # get stick
    kl = klines(symbol)
    ema_indicator = ta.trend.ema_indicator(kl.Close)
    return round(ema_indicator.iloc[-1], 2)

print(f"EMA: {EMA_signal('ETHUSDT')}")

# usecase
#adx, adx_plus, adx_minus = adx_signal("ETHUSDT")
#print(f"ADX: {round(adx, 2)}, ADX+: {round(adx_plus,2)}, ADX-: {round(adx_minus,2)}")

max_pos = 10
symbols = get_tickers()
#symbols = ["ETHUSDT", "BTCUSDT", "XRPUSDT", "ADAUSDT"]

while True:
    balance = round(BalanceAccount(),2)
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
                signal_rsi = rsi_signal(elem)
                signal_adx = adx_signal(elem)

                print(elem, signal_adx)

                if signal_rsi[0] == 'up' and not elem in pos:
                    print (f'Found RSI BUY signal for {elem}')
                    if signal_adx == 'up' and not elem in pos:
                        print (f'Found ADX BUY signal for {elem}')
                        set_mode(elem)
                        sleep(2)
                        place_order_market(elem, "Buy")
                        sleep(5)
                if signal_rsi[0] == 'down' and not elem in pos:
                    print (f'Found RSI SELL signal for {elem}')
                    if signal_adx == 'down' and not elem in pos:
                        print (f'Found ADX SELL signal for {elem}')
                        set_mode(elem)
                        sleep(2)
                        place_order_market(elem, "Sell")
                        sleep(5)
    print("waiting 2 minutes")
    sleep(120)