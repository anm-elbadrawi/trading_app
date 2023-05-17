from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.contract import *
from ibapi.order import Order
import pandas as pd
import threading
import time
import math
import numpy as np
import random

def closest(lst, K):
    return lst[min(range(len(lst)), key = lambda i: abs(lst[i]-K))]

df1 = {}
options_df = {}
strikes_df = {}
conids = []
options_price = []
temp_options_price = {}
price_df = {}


expiry_date = 20210611
stop_loss_percent = 50
profit_percent = 50

tickers = ["AAPL", "TSLA", "NVDA", "AMD"]

capital = 10000

options_price_df = {}

class TradeApp(EWrapper, EClient): 
    def __init__(self): 
        EClient.__init__(self, self) 
        self.data = {}
        self.contractdata = {}
        self.options_data = {}
        self.pos_df = pd.DataFrame(columns=['Account', 'Symbol', 'SecType',
                                    'Currency', 'Position', 'Avg cost'])
        self.order_df = pd.DataFrame(columns=['PermId', 'ClientId', 'OrderId',
                                          'Account', 'Symbol', 'SecType',
                                          'Exchange', 'Action', 'OrderType',
                                          'TotalQty', 'CashQty', 'LmtPrice',
                                          'AuxPrice', 'Status'])
        
    def historicalData(self, reqId, bar):
        print(f'Time: {bar.date}, Open: {bar.open}, Close: {bar.close}')
        if reqId not in self.data:
            self.data[reqId] = [{"Date":bar.date,"Open":bar.open,"High":bar.high,"Low":bar.low,"Close":bar.close,"Volume":bar.volume}]
        else:
            self.data[reqId].append({"Date":bar.date,"Open":bar.open,"High":bar.high,"Low":bar.low,"Close":bar.close,"Volume":bar.volume})

    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        print("NextValidId:", orderId)
        
    def position(self, account, contract, position, avgCost):
        super().position(account, contract, position, avgCost)
        dictionary = {"Account":account, "Symbol": contract.symbol, "SecType": contract.secType,
                      "Currency": contract.currency, "Position": position, "Avg cost": avgCost}
        self.pos_df = self.pos_df.append(dictionary, ignore_index=True)
        
    def positionEnd(self):
        print("Latest position data extracted")
        
    def openOrder(self, orderId, contract, order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        dictionary = {"PermId":order.permId, "ClientId": order.clientId, "OrderId": orderId, 
                      "Account": order.account, "Symbol": contract.symbol, "SecType": contract.secType,
                      "Exchange": contract.exchange, "Action": order.action, "OrderType": order.orderType,
                      "TotalQty": order.totalQuantity, "CashQty": order.cashQty, 
                      "LmtPrice": order.lmtPrice, "AuxPrice": order.auxPrice, "Status": orderState.status}
        self.order_df = self.order_df.append(dictionary, ignore_index=True)
        
    def contractDetails(self, reqId, contractDetails):
        print(f"Contract Details:   {contractDetails}\n\n")
        if reqId not in self.contractdata:
            self.contractdata[reqId] = [{"Data": contractDetails}]
        else:
            self.contractdata[reqId].append({"Data": contractDetails})
        
    def contractDetailsEnd(self, reqId):
        print("\ncontractDetails End\n")
        
    def tickPrice(self, reqId, tickType, price, attrib):
        super().tickPrice(reqId, tickType, price, attrib)
        print("-asdhjvqwhdqdgkvqwdqvdwhqwvgdqw-")
        print(f"Tick Type: {tickType}, price:   {price}")
        if reqId not in self.options_data:
            self.options_data[reqId] = [{"Price": price}]
        else:
            self.options_data[reqId].append({"Price": price})   
        print("snap done")



def usTechStk(symbol,sec_type="STK",currency="USD",exchange="ISLAND"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.currency = currency
    contract.exchange = exchange
    return contract 

def optionContract(symbol, expiry, sec_type="OPT", currency="USD", exchange="SMART"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.currency = currency
    contract.exchange = exchange
    contract.lastTradeDateOrContractMonth = expiry
    return contract

def optionSpread(symbol, conid1, conid2, expiry = expiry_date, sec_type="BAG", currency="USD", exchange="SMART"):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.currency = currency
    contract.exchange = exchange
    contract.lastTradeDateOrContractMonth = expiry
    
    leg1 = ComboLeg()
    leg1.conId = conid1
    leg1.ratio = 1
    leg1.action = "SELL"
    leg1.exchange = exchange

    leg2 = ComboLeg()
    leg2.conId = conid2
    leg2.ratio = 1
    leg2.action = "BUY"
    leg2.exchange = exchange 
    
    contract.comboLegs = []
    contract.comboLegs.append(leg1)
    contract.comboLegs.append(leg2)
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
                          chartOptions=[])
    
def streamSnapshotData(req_num, contract):
    app.reqMarketDataType(2)
    app.reqMktData(reqId = req_num,
                   contract = contract,
                   genericTickList = "",
                   snapshot = True,
                   regulatorySnapshot = False,
                   mktDataOptions = [])
    #app.tickSnapshotEnd(reqId = req_num)
    #app.cancelTickByTickData(reqId = req_num)

def websocket_con():
    app.run()

app = TradeApp()
app.connect(host='127.0.0.1', port=7497, clientId=1) #port 4002 for ib gateway paper trading/7497 for TWS paper trading
con_thread = threading.Thread(target=websocket_con, daemon=True)
con_thread.start()

##############################################################################

def dataDataframe(TradeApp_obj,symbols, symbol):
    "returns extracted historical data in dataframe format"
    df = pd.DataFrame(TradeApp_obj.data[symbols.index(symbol)])
    df.set_index("Date",inplace=True)
    return df

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


def marketOrder(direction,quantity):
    order = Order()
    order.action = direction
    order.orderType = "MKT"
    order.totalQuantity = quantity
    return order

def stopOrder(direction,quantity,st_price):
    order = Order()
    order.action = direction
    order.orderType = "STP"
    order.totalQuantity = quantity
    order.auxPrice = st_price
    return order

def limitOrder(direction,quantity, lmt_price):
    order = Order()
    order.action = direction
    order.orderType = "LMT"
    order.totalQuantity = quantity
    order.lmtPrice = lmt_price
    return order

def limitTriggerOrder(direction, quantity, lmt_price, trigger_price):
    order = Order()
    order.action = direction
    order.orderType = "LIT"
    order.totalQuantity = quantity
    order.lmtPrice = lmt_price
    order.AuxPrice = trigger_price
    return order

###############################################################################

def main():
    app.data = {}
    app.pos_df = pd.DataFrame(columns=['Account', 'Symbol', 'SecType',
                            'Currency', 'Position', 'Avg cost'])
    app.order_df = pd.DataFrame(columns=['PermId', 'ClientId', 'OrderId',
                                      'Account', 'Symbol', 'SecType',
                                      'Exchange', 'Action', 'OrderType',
                                      'TotalQty', 'CashQty', 'LmtPrice',
                                      'AuxPrice', 'Status'])
    app.reqPositions()
    time.sleep(2)
    pos_df = app.pos_df
    pos_df.drop_duplicates(inplace=True,ignore_index=True) # position callback tends to give duplicate values
    app.reqOpenOrders()
    time.sleep(2)
    ord_df = app.order_df
        
    
    for ticker in tickers:
        print("starting passthrough for.....",ticker)
        histData(tickers.index(ticker),usTechStk(ticker),'2 D', '5 mins')
        time.sleep(3.0) 
        df = dataDataframe(app,tickers,ticker)
        
        app.reqContractDetails(tickers.index(ticker), optionContract(symbol = ticker, expiry = expiry_date)) #SET EXPIRY EVERY WEEK
        time.sleep(3)
        df1[ticker] = pd.DataFrame(data = app.contractdata[tickers.index(ticker)])
        
        for i in range(len(df1[ticker])):
            df1[ticker]["Data"][i] = str(df1[ticker]["Data"][i]).split(",")  

        conid_list = []     
        strikes_list = []
        type_list = []
        strikes_list_label = []
        
        for i in range(len(df1[ticker])):
            strikes_list.append(df1[ticker]["Data"][i][4])
            type_list.append(df1[ticker]["Data"][i][5])
            conid_list.append(df1[ticker]["Data"][i][0])
            
        for i in range(len(df1[ticker])):
            strikes_list_label.append(str(strikes_list[i]) + str(df1[ticker]["Data"][i][5]))
            #strikes_list[i] = str(strikes_list[i]) + str(df1[ticker]["Data"][i][5])
        
        options_dict = {"conId": conid_list, "Strikes": strikes_list, "Type": type_list, "Strikes_Label": strikes_list_label}
        
        options_df[ticker] = pd.DataFrame(data = options_dict)
        options_df[ticker].sort_values(by=["Strikes"], inplace=True)

        numbers_list = []
        [numbers_list.append(float(x)) for x in options_df[ticker]["Strikes"]]
        strikes_dict = {"Strikes": numbers_list}
        strikes_df[ticker] = pd.DataFrame(data = strikes_dict)
        strikes_df[ticker].sort_values(by=["Strikes"], inplace=True)
        
        numbers_list2 = []
        [numbers_list2.append(float(x)) for x in numbers_list if x not in numbers_list2]
        numbers_list2.sort()
        numbers_list3 = numbers_list2
        numbers_list2 = map(str, numbers_list2)
        strikes_dict2 = {"Strikes": numbers_list2}
        strikes_df[ticker] = pd.DataFrame(data = strikes_dict2)


        def find_conid(type:str, offset:int):
            if type == "P":
                close_closest_strike = closest(numbers_list3, float(math.floor(df["Close"][-1])))
                conids.append(f"closest: {close_closest_strike}")
                for i in range(len(strikes_df[ticker]["Strikes"])):
                    if str(float(close_closest_strike)) in strikes_df[ticker]["Strikes"][i]:
                        shifted_strike = strikes_df[ticker]["Strikes"][i-offset]
                        break
                for i in range(len(options_df[ticker]["Strikes_Label"])):
                    if (str(shifted_strike) + type) in options_df[ticker]["Strikes_Label"][i]:
                        conid_find = options_df[ticker]["conId"][i]
                        conids.append(f"{ticker} {conid_find}")
                        return conid_find   
                    else:
                        conids.append("Nothing")
                        
            if type == "C":
                close_closest_strike = closest(numbers_list3, float(math.ceil(df["Close"][-1])))
                conids.append(f"closest: {close_closest_strike}")
                for i in range(len(strikes_df[ticker]["Strikes"])):
                    if str(float(close_closest_strike)) in strikes_df[ticker]["Strikes"][i]:
                        shifted_strike = strikes_df[ticker]["Strikes"][i+offset]
                        break
                for i in range(len(options_df[ticker]["Strikes_Label"])):
                    if (str(shifted_strike) + type) in options_df[ticker]["Strikes_Label"][i]:
                        conid_find = options_df[ticker]["conId"][i]
                        conids.append(f"{ticker} {conid_find}")
                        return conid_find   
                    else:
                        conids.append("Nothing")             
        time.sleep(1)

        
        df["BB UP"] = bollBnd(df)["BB_up"]
        df["BB DOWN"] = bollBnd(df)["BB_dn"]
        df["EMA 21"] = eMA21(df)
        df["EMA 55"] = eMA55(df)
        df.dropna(inplace=True)
    
        quantity = int(capital/df["Close"][-1])
        if quantity == 0:
            continue
        
        options_price = []
        
        def placeorder_func(type:str):
            app.reqIds(-1)
            time.sleep(2)
            streamSnapshotData(tickers.index(ticker), optionSpread(ticker, conid1 = find_conid(type, 1), conid2 = find_conid(type, 4)))
            time.sleep(4)
            price_df[ticker] = pd.DataFrame(data = app.options_data[tickers.index(ticker)])
            mid_price = ((price_df[ticker]["Price"].iloc[-1])+(price_df[ticker]["Price"].iloc[-2]))/2
            mid_price_rounded = round(mid_price, 2)
            options_price.append(((mid_price_rounded)))
            order_id = app.nextValidOrderId
            app.placeOrder(order_id,optionSpread(ticker, conid1 = find_conid(type, 1), conid2 = find_conid(type, 4)),limitOrder("BUY",quantity,mid_price_rounded))
            #app.placeOrder(order_id+1,optionSpread(ticker, conid1 = find_conid(type, 1), conid2 = find_conid(type, 4)),stopOrder("SELL",quantity,round(((100+stop_loss_percent)/100)*options_price[-1],2)))
            #app.placeOrder(order_id+2,optionSpread(ticker, conid1 = find_conid(type, 1), conid2 = find_conid(type, 4)),limitTriggerOrder("SELL", quantity, (round(((100-profit_percent)/100)*options_price[-1],2)), (round(((100-profit_percent+10)/100)*options_price[-1],2))))
        
        
        
        if len(pos_df)==0:
            if (df["Close"][-1]> df["BB UP"][-1] and df["EMA 21"][-1]> df["EMA 55"][-1]):
                placeorder_func("P")
            elif (df["Close"][-1]< df["BB DOWN"][-1] and df["EMA 21"][-1]< df["EMA 55"][-1]):
                placeorder_func("C")
            
        elif len(pos_df)!=0 and ticker not in pos_df["Symbol"].tolist():
            if (df["Close"][-1]> df["BB UP"][-1] and df["EMA 21"][-1]> df["EMA 55"][-1]):
                placeorder_func("P")
            elif (df["Close"][-1]< df["BB DOWN"][-1] and df["EMA 21"][-1]< df["EMA 55"][-1]):
                placeorder_func("C")
                
        elif len(pos_df)!=0 and ticker in pos_df["Symbol"].tolist():
            if pos_df[pos_df["Symbol"]==ticker]["Position"].sort_values(ascending=True).values[-1] == 0:
                if (df["Close"][-1]> df["BB UP"][-1] and df["EMA 21"][-1]> df["EMA 55"][-1]):
                    placeorder_func("P")
                elif (df["Close"][-1]< df["BB DOWN"][-1] and df["EMA 21"][-1]< df["EMA 55"][-1]):
                    placeorder_func("C")
                    
        time.sleep(5)
                    
    print(df["Close"][-1])
    print(pos_df)
   
        


#extract and store historical data in dataframe repetitively
starttime = time.time()
timeout = time.time() + 60*60*6
while time.time() <= timeout:
    main()
    time.sleep(300 - ((time.time() - starttime) % 300.0))


