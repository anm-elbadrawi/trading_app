from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import pandas as pd
import threading
import time
from copy import deepcopy
import numpy as py
import numpy as np
import matplotlib.pyplot as plt

plt.close("all")

class TradeApp(EWrapper, EClient): 
    def __init__(self): 
        EClient.__init__(self, self) 
        self.data = {}
        
    def historicalData(self, reqId, bar):
        if reqId not in self.data:
            self.data[reqId] = [{"Date":bar.date,"Open":bar.open,"High":bar.high,"Low":bar.low,"Close":bar.close,"Volume":bar.volume}]
        else:
            self.data[reqId].append({"Date":bar.date,"Open":bar.open,"High":bar.high,"Low":bar.low,"Close":bar.close,"Volume":bar.volume})
        print("reqID:{}, date:{}, open:{}, high:{}, low:{}, close:{}, volume:{}".format(reqId,bar.date,bar.open,bar.high,bar.low,bar.close,bar.volume))

def usTechStk(symbol,sec_type="STK",currency="USD",exchange="ISLAND"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.currency = currency
    contract.exchange = exchange
    return contract 

def histData(req_num,contract,duration,candle_size):
    """extracts historical data"""
    app.reqHistoricalData(reqId=req_num, 
                          contract=contract,
                          endDateTime='',
                          durationStr=duration,
                          barSizeSetting=candle_size,
                          whatToShow='ADJUSTED_LAST',
                          useRTH=1,
                          formatDate=1,
                          keepUpToDate=0,
                          chartOptions=[])	 # EClient function to request contract details

def websocket_con():
    app.run()
    
app = TradeApp()
app.connect(host='127.0.0.1', port=4002, clientId=2) #port 4002 for ib gateway paper trading/7497 for TWS paper trading
con_thread = threading.Thread(target=websocket_con, daemon=True)
con_thread.start()
time.sleep(1) # some latency added to ensure that the connection is established

tickers = ["FB", "AAPL", "AMD", "NVDA"]
for ticker in tickers:
    histData(tickers.index(ticker),usTechStk(ticker),'30 D', '5 mins')
    time.sleep(5)

###################storing trade app object in dataframe#######################
def dataDataframe(symbols,TradeApp_obj):
    "returns extracted historical data in dataframe format"
    df_data = {}
    for symbol in symbols:
        df_data[symbol] = pd.DataFrame(TradeApp_obj.data[symbols.index(symbol)])
        df_data[symbol].set_index("Date",inplace=True)
    return df_data

#extract and store historical data in dataframe
historicalData = dataDataframe(tickers,app)
###############################################################################

def bollBnd(DF,n=20):
    "function to calculate Bollinger Band"
    df = DF.copy()
    #df["MA"] = df['close'].rolling(n).mean()
    df["MA"] = df['Close'].ewm(span=n,min_periods=n).mean()
    df["BB_up"] = df["MA"] + 2*df['Close'].rolling(n).std(ddof=0) 
    df["BB_dn"] = df["MA"] - 2*df['Close'].rolling(n).std(ddof=0) 
    df["BB_width"] = df["BB_up"] - df["BB_dn"]
    df.dropna(inplace=True)
    return df

def eMA21(DF,a=21):
    df = DF.copy()
    df["EMA 21"] = df["Close"].ewm(span=a, min_periods=a).mean()
    return df["EMA 21"]

def eMA55(DF,a=55):
    df = DF.copy()
    df["EMA 55"] = df["Close"].ewm(span=a, min_periods=a).mean()
    return df["EMA 55"]

boll_df = {}
for ticker in tickers:
    boll_df[ticker] = bollBnd(DF = historicalData[ticker])
    
ema21_df = {}
for ticker in tickers:
    ema21_df[ticker] = eMA21(DF = historicalData[ticker])
    
ema55_df = {}
for ticker in tickers:
    ema55_df[ticker] = eMA55(DF = historicalData[ticker])


#############################backtesting######################################

ohlc_dict = deepcopy(historicalData)
ticker_signal = {}
ticker_ret = {}
trade_count = {}

for ticker in tickers:
    ohlc_dict[ticker]["BB UP"] = bollBnd(DF = ohlc_dict[ticker])["BB_up"]
    ohlc_dict[ticker]["BB DOWN"] = bollBnd(DF = ohlc_dict[ticker])["BB_dn"]
    ohlc_dict[ticker]["EMA 21"] = eMA21(DF = ohlc_dict[ticker])
    ohlc_dict[ticker]["EMA 55"] = eMA55(DF = ohlc_dict[ticker])
    ohlc_dict[ticker].dropna(inplace=True)
    trade_count[ticker] = 0
    ticker_signal[ticker] = ""
    ticker_ret[ticker] = [0]

for ticker in tickers:
    for i in range(1,len(ohlc_dict[ticker])):
        if ticker_signal[ticker] == "":
            ticker_ret[ticker].append(0)
            if (ohlc_dict[ticker]["Close"][i] > ohlc_dict[ticker]["BB UP"][i]) and (ohlc_dict[ticker]["EMA 21"][i] > ohlc_dict[ticker]["EMA 55"][i]):
                    ticker_signal[ticker] = "Buy"
                    trade_count[ticker] += 1
                    buy_price = ohlc_dict[ticker]["Close"][i]
                    
        elif ticker_signal[ticker] == "Buy":
            if (ohlc_dict[ticker]["Close"][i] <= ohlc_dict[ticker]["EMA 21"][i]):
                ticker_signal[ticker] = ""
                trade_count[ticker] += 1
                ticker_ret[ticker].append("Final Return:   " + str(round((((ohlc_dict[ticker]["Close"][i] / buy_price)-1)*100),3)))
            else:
                ticker_ret[ticker].append("In Progress: " + str(round((((ohlc_dict[ticker]["Close"][i] / buy_price)-1)*100),3)))
                    
                
    ohlc_dict[ticker]["ret"] = np.array(ticker_ret[ticker]) 




##############################formatting final_return to remove "Final Return:   "############ 
final_return = {}
for ticker in tickers:
    final_return[ticker] = []

for ticker in tickers:
    for i in range(len(ohlc_dict[ticker])):
        if "Final Return" in ohlc_dict[ticker]["ret"][i]:
            final_return[ticker].append(ohlc_dict[ticker]["ret"][i])



total_return = {}
for ticker in tickers:
    total_return[ticker] = []

final_return_copy = final_return.copy()
for ticker in tickers:
    for i in range(0, len(final_return[ticker])):
        final_return_copy[ticker][i] = float(final_return_copy[ticker][i].replace("Final Return:   ", ""))

####theoretical value of $1000#################################################

balance = 100000
start_balance = balance

balance_ftime ={}
for ticker in tickers:
    balance_ftime[ticker] = []

for ticker in tickers:
    balance = 100000
    for i in range(0, len(final_return[ticker])):
        balance *= (1 + (final_return_copy[ticker][i])/100)
        balance_ftime[ticker].append(balance)
        print(ticker)
        print(f"${round(balance,2)}")

for ticker in tickers:
    #ror = round((((balance_ftime[ticker][-1] - balance_ftime[ticker][0])/balance_ftime[ticker][0])*100), 2)
    ror = round((((balance_ftime[ticker][-1] - start_balance)/start_balance)*100), 2)
    balance = round(balance, 2)
    
    #print(f"\n\n\nBacktest: \nThe starting balance for {ticker} was {round(balance_ftime[ticker][0], 2)}. \nThe ending balance is {round(balance_ftime[ticker][-1], 2)}. \nThis is equal to a return of {ror}%")
    print(f"\n\n\nBacktest: \nThe starting balance for {ticker} was {start_balance}. \nThe ending balance is {round(balance_ftime[ticker][-1], 2)}. \nThis is equal to a return of {ror}%")

